"""Versioned, deterministic GitHub TS -> Python ESSE boundary.

A mask is 100000 bits, little-endian within each byte (ID 00000 is bit 0).
The browser computes the TypeScript rule masks; this module checks their
integrity, counts, strict-conjunction parity and source-domain invariants.
This does *not* claim an independent implementation of every TS rule.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

import numpy as np

from .sculpting import Knife, SculptSession, N
from .github_rule_parity import evaluate_basic

SCHEMA = "pl5-esse-bridge-v1"
BIT_BYTES = N // 8
MAX_RULES = 20

class ContractError(ValueError):
    pass


def decode_mask(item: dict[str, Any]) -> np.ndarray:
    if not isinstance(item, dict) or item.get("encoding") != "bitset-lsb0-base64":
        raise ContractError("位图编码必须为bitset-lsb0-base64")
    encoded = item.get("bits")
    if not isinstance(encoded, str) or len(encoded) > 17000:
        raise ContractError("位图文本无效或过长")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContractError("无效的base64位图") from exc
    if len(raw) != BIT_BYTES:
        raise ContractError("位图必须恰好12500字节")
    digest = hashlib.sha256(raw).hexdigest()
    if not isinstance(item.get("sha256"), str) or item["sha256"] != digest:
        raise ContractError("位图SHA256校验失败")
    arr = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little").astype(bool)
    claimed = item.get("count")
    if type(claimed) is not int or claimed != int(arr.sum()):
        raise ContractError("位图count不匹配")
    return arr


def encode_mask(mask: np.ndarray) -> dict:
    arr = np.asarray(mask, dtype=bool)
    if arr.shape != (N,):
        raise ContractError("必须恰好100000位")
    raw = np.packbits(arr.astype(np.uint8), bitorder="little").tobytes()
    return {"encoding":"bitset-lsb0-base64", "bits":base64.b64encode(raw).decode("ascii"),
            "sha256":hashlib.sha256(raw).hexdigest(), "count":int(arr.sum())}


def _text(value: Any, field: str, limit: int = 120) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or "\x00" in value:
        raise ContractError(f"{field}必须为非空短字符串")
    return value


def run_bridge(request: dict[str, Any], *, registry=None) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != SCHEMA:
        raise ContractError("接口协议版本不受支持")
    if request.get("combination") != "strict":
        raise ContractError("V1.2仅支持严格AND；容错模式不得被错误转换为AND")
    k = request.get("k", 100)
    if type(k) is not int or not 1 <= k <= 100:
        raise ContractError("候选预算须为1至100")
    seed = request.get("seed", 20261101)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ContractError("随机种子须为32位非负整数")
    base = decode_mask(request.get("base"))
    base_count = int(base.sum())
    if base_count == 0:
        raise ContractError("来源号码集合为空")
    rules = request.get("rules")
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        raise ContractError("规则数不得超过20")
    keys = set()
    independently_verified = []
    unverified_types = []
    knives = []
    enabled = ["__source__"]
    # Mask outside the source is a hard guard.  Never treat it as a user knife.
    knives.append(Knife("__source__","来源域固定约束",~base,group="system-source",weight=10))
    conjunct = base.copy()
    for item in rules:
        if not isinstance(item, dict):
            raise ContractError("规则对象无效")
        key = _text(item.get("id"), "规则id", 100)
        if key == "__source__" or key in keys:
            raise ContractError("规则id冲突")
        keys.add(key)
        label = _text(item.get("label"), "规则label")
        group = _text(item.get("group"), "规则group", 100)
        rule_keep = decode_mask(item.get("kept"))
        if bool(np.any(rule_keep & ~base)):
            raise ContractError("规则掩码超出来源集合")
        excluded = base & ~rule_keep
        spec = item.get("rule_spec")
        if spec is not None:
            if not isinstance(spec,dict) or spec.get("id") != key:
                raise ContractError("rule_spec的ID与规则ID不一致")
            try:
                independent = evaluate_basic(spec)
            except ValueError as exc:
                raise ContractError(f"独立规则复算参数错误: {exc}") from exc
            if independent is not None:
                if not np.array_equal(base & independent, rule_keep):
                    raise ContractError(f"规则{key}的TypeScript/Python完整位图不一致")
                independently_verified.append(key)
            else:
                unverified_types.append(str(spec.get("kind")))
        else:
            unverified_types.append("missing_rule_spec")
        if item.get("enabled") is not True:
            raise ContractError("只允许传输已启用的规则")
        knives.append(Knife(key,label,excluded,group=group,source="github-rule-mask",weight=1.0))
        enabled.append(key)
        conjunct &= rule_keep
    expected = request.get("expected_strict_keep")
    if type(expected) is not int or not 0 <= expected <= base_count:
        raise ContractError("缺少原生TypeScript严格AND结果数量")
    actual = int(conjunct.sum())
    strict_keep = request.get("strict_kept")
    if request.get("protocol_upgrade") == "v13_verified" and strict_keep is None:
        raise ContractError("V1.3必须提供原生最终严格AND完整位图")
    strict_mask_verified = False
    if strict_keep is not None:
        strict_mask_verified = np.array_equal(decode_mask(strict_keep),conjunct)
        if not strict_mask_verified:
            raise ContractError("最终TypeScript严格AND位图与Python交集不同")
    if expected != actual:
        raise ContractError(f"两端严格AND交集不一致：TS={expected}，掩码={actual}")
    ts_only_count = actual
    registered = request.get("registered_rule_ids", [])
    if not isinstance(registered, list) or len(registered)>10 or len(set(map(str,registered)))!=len(registered):
        raise ContractError("注册算法ID必须是最多10个不重复值")
    if registered and registry is None:
        raise ContractError("未配置本地算法准入库，拒绝启用注册规则")
    registered_receipts = []
    if registered:
        meta = request.get("meta", {})
        cutoff = meta.get("reference_issue") if isinstance(meta,dict) else None
        if not cutoff:
            raise ContractError("实验规则必须指定准确的历史截止期号")
        for key in registered:
            if not isinstance(key,str) or not re.fullmatch(r"[0-9a-f]{64}",key):
                raise ContractError("注册规则ID无效")
            try:
                data = registry.get(key)
                ban = registry.mask(key, require_approval=True, cutoff_issue=cutoff)
                if data["source_mask_sha256"] != encode_mask(base)["sha256"]:
                    raise PermissionError("算法来源域与本次过滤号码大底不同")
            except (ValueError, KeyError, PermissionError) as exc:
                raise ContractError("注册规则未通过准入门禁："+str(exc)) from exc
            if not registry.verify_ledger():
                raise ContractError("算法审批事件链校验失败")
            # A registered rule is restricted to the TS source domain; no
            # externally supplied mask or client-supplied evidence is trusted.
            ban = base & ban
            knife_id = "registry:" + key
            knives.append(Knife(knife_id,data["title"],ban,group="registered:"+data["family"],
                                source="local-reviewed-experiment",weight=1.0,
                                evidence="experimental_only"))
            enabled.append(knife_id)
            conjunct &= ~ban
            registered_receipts.append({"id":key,"mask_sha256":data["mask_sha256"],
                                        "cutoff_issue":data["cutoff_issue"],
                                        "experimental_only":True})
    actual = int(conjunct.sum())
    session = SculptSession(knives,enabled=enabled,seed=seed)
    art = session.sculpt()
    if not np.array_equal(art.kept_mask,conjunct):
        raise ContractError("Python ESSE计算与掩码交集不一致")
    # Rank *inside source only*. The older V1.1 quota-repair can otherwise
    # revive numbers outside an imported external candidate set.
    ids = np.flatnonzero(base)
    rng = np.random.default_rng(seed)
    # Deterministic random tie breaker, not a predictive feature.
    tie = rng.permutation(N).astype(np.int32)
    order = np.lexsort((tie[ids],art.penalty[ids],(~art.kept_mask[ids]).astype(np.uint8)))
    ranked = ids[order]
    chosen = ranked[:min(k,base_count)]
    restored = int((~art.kept_mask[chosen]).sum())
    meta = request.get("meta", {})
    if not isinstance(meta, dict):
        raise ContractError("meta必须是对象")
    history_source = meta.get("history_source", "未标注")
    if not isinstance(history_source,str) or len(history_source)>200:
        raise ContractError("历史来源标记无效")
    cutoff = meta.get("reference_issue")
    if cutoff is not None and (not isinstance(cutoff,str) or not re.fullmatch(r"\d{1,20}",cutoff)):
        raise ContractError("参考期号无效")
    result = {
        "schema": SCHEMA,
        "engine": "PL5-ESSE-Python-V1.2",
        "reference_issue": cutoff,
        "history_source_label": history_source,
        "history_source_verified_by_backend": False,
        "base_count": base_count,
        "strict_keep_count":actual,
        "typescript_strict_keep_count":ts_only_count,
        "registered_rule_count":len(registered_receipts),
        "registered_experimental_rules":registered_receipts,
        "registered_rules_are_predictive":False,
        "expected_strict_keep":expected,
        "parity_count_verified":True,
        "full_mask_parity_verified":strict_mask_verified,
        "independent_rule_count":len(independently_verified),
        "independent_rule_ids":independently_verified,
        "unverified_rule_types":unverified_types,
        "selected_count":len(chosen),
        "requested_k":k,
        "top_numbers":[f"{n:05d}" for n in chosen],
        "top_items":[{"number":f"{n:05d}","hard_kept":bool(art.kept_mask[n]),
                      "uncalibrated_penalty":round(float(art.penalty[n]),8)} for n in chosen],
        "restored_for_quota": restored,
        "steps":[x.as_dict() for x in art.stages],
        "marginals":[x for x in session.counterfactual() if x["key"]!="__source__"],
        "fair_random_single_draw_coverage":len(chosen)/N,
        "fair_random_10_draw_coverage":1-(1-len(chosen)/N)**10,
        "statistical_status":"NO_PREDICTIVE_ADVANTAGE_ESTABLISHED",
        "protocol_warning":"TypeScript完整位图仅校核原生规则；注册的实验刀由本地审批库读取并叠加，不是彩票预测依据。",
        "source_guard":bool(np.all(base[chosen]))
    }
    # JSON-safe deterministic audit hash of *input* only, without provenance inflation.
    result["request_sha256"] = hashlib.sha256(json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return result
