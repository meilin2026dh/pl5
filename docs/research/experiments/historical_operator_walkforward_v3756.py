"""V3.7.56 frozen multi-operator retrospective forward-window coverage audit.

Do not use the target outcome for construction or parameter selection.
Read-only byte-verified two-publisher transcriptions; not source-authenticated.
"""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "pl5-cumulative" / "research_backend"))
sys.path.insert(0, str(HERE))
from conditional_complementarity_v3752 import new_signatures
from spectral_independence_v3754 import spectral_invariants

DOMAIN = 100_000
WARMUP = 31
TEST_WINDOWS = 20
RULE_NAMES = (
    "mod2_zero", "mod3_zero", "mod5_zero", "mod7_zero", "mod11_zero",
    "mod13_zero", "omega_ge3", "bigomega_ge3", "squarefree_one",
    "spectral_C1_gt_C2",
)
PRIMARY = ROOT / "pl5-cumulative" / "data" / "official_transcriptions_v3719" / "jiangsu_transcribed.csv"
WITNESS = ROOT / "pl5-cumulative" / "data" / "official_transcriptions_v3719" / "gansu_transcribed.csv"
EXPECTED_HASHES = {
    "primary": "6962260131f6f78072bb4b0ec95514ff8ec764e1d3a2048a275e06a24644b00e",
    "witness": "ca0c2ef7ff02dedc8d467a0ae1c829683339f7831911b520694cb6af7df9da26",
}
FAMILY_MASKS = {"modular": 63, "prime_factor": 448, "spectral": 512}


def parse_csv(path, expected_sha):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha:
        raise ValueError("historical bytes differ from frozen source digest")
    reader = csv.DictReader(raw.decode("utf-8-sig").splitlines())
    if reader.fieldnames != ["issue", "number"]:
        raise ValueError("unexpected historical CSV schema")
    rows = []
    last = -1
    for item in reader:
        issue, value = item["issue"], item["number"]
        if not (issue.isascii() and issue.isdigit() and len(value) == 5
                and value.isascii() and value.isdigit()
                and 0 <= int(value) < DOMAIN and int(issue) > last):
            raise ValueError("invalid chronology or five-digit identity")
        rows.append((issue, value))
        last = int(issue)
    return rows


def verified_rows():
    a = parse_csv(PRIMARY, EXPECTED_HASHES["primary"])
    b = parse_csv(WITNESS, EXPECTED_HASHES["witness"])
    if len(a) != 51 or len(b) != TEST_WINDOWS:
        raise ValueError("source sample count changed")
    if a[WARMUP:] != b:
        raise ValueError("crosschecked outcome window does not agree")
    if a[0][0] != "26244" or a[-1][0] != "26294":
        raise ValueError("source boundaries drifted")
    if any(int(y[0]) != int(x[0]) + 1 for x,y in zip(a,a[1:])):
        raise ValueError("missing issue in frozen chronology")
    return a


def masks():
    # Predeclared predicates from V3.7.51 and V3.7.54;
    # source and test window are not inspected to construct these masks.
    prior = new_signatures()
    if len(prior) != DOMAIN:
        raise AssertionError("static number-theoretic feature drift")
    flags = [int(prior[n]) | (int(spectral_invariants(n)[1] > 0) << 9)
             for n in range(DOMAIN)]
    keep = [bytearray(DOMAIN // 8) for _ in RULE_NAMES]
    for n, flag in enumerate(flags):
        for j, data in enumerate(keep):
            if flag & (1 << j):
                data[n >> 3] |= 1 << (n & 7)
    bitmap = tuple(int.from_bytes(row, "little") for row in keep)
    if len(bitmap) != 10:
        raise AssertionError("rule inventory drift")
    return bitmap


def all_coalitions(rule_masks):
    full = (1 << DOMAIN) - 1
    result = [full] * (1 << len(rule_masks))
    for s in range(1, len(result)):
        low = s & -s
        result[s] = result[s ^ low] & rule_masks[low.bit_length()-1]
    return result


def declared_arms():
    arms = {name: 1 << i for i,name in enumerate(RULE_NAMES)}
    for f in range(1, 8):
        mask = 0
        for i,(_, group) in enumerate(FAMILY_MASKS.items()):
            if f & (1 << i):
                mask |= group
        arms["family_" + "_".join(
            name for i,name in enumerate(FAMILY_MASKS) if f & (1 << i))] = mask
    assert len(arms) == 17 and arms["family_modular_prime_factor_spectral"] == 1023
    return arms


def history_digest(rows):
    return sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def random_control(prefix_digest, issue, arm, k, target=None):
    # Retrospective scorer must not pass the target; test hook accepts it
    # solely to assert it is never used in seed derivation.
    token = (prefix_digest + "|" + issue + "|" + arm + "|v3756").encode()
    seed = int.from_bytes(sha256(token).digest(), "big")
    return frozenset(random.Random(seed).sample(range(DOMAIN), k))


def run():
    rows = verified_rows()
    rule_masks = masks()
    coalitions = all_coalitions(rule_masks)
    arms = declared_arms()
    frozen = [
        {"coalition": s, "candidate_count": bm.bit_count(),
         "bitmap_sha256": sha256(bm.to_bytes(DOMAIN//8, "little")).hexdigest()}
        for s,bm in enumerate(coalitions)
    ]
    if frozen[0]["candidate_count"] != DOMAIN:
        raise AssertionError("domain drift")
    # Static arrays/fingerprints fixed before any outcome is inspected.
    ledger = {name: [] for name in arms}
    totals = [0] * len(coalitions)
    baseline_totals = {name: 0 for name in arms}
    for idx in range(WARMUP, len(rows)):
        issue = rows[idx][0]
        prefix = rows[:idx]
        phash = history_digest(prefix)
        # Freeze all 17 arm controls and all 1024 static memberships before
        # reading the target number for this issue.
        controls = {name: random_control(phash, issue, name,
                    frozen[s]["candidate_count"]) for name,s in arms.items()}
        commitments = {name: sha256(",".join(f"{n:05d}" for n in sorted(values)).encode()).hexdigest()
                       for name,values in controls.items()}
        target = int(rows[idx][1])
        hits = [int((bm >> target) & 1) for bm in coalitions]
        totals = [count + hit for count,hit in zip(totals,hits)]
        for name, s in arms.items():
            control_hit = int(target in controls[name])
            baseline_totals[name] += control_hit
            ledger[name].append({
                "issue": issue, "prefix_count": idx,
                "prefix_sha256": phash, "candidate_count": frozen[s]["candidate_count"],
                "candidate_sha256": frozen[s]["bitmap_sha256"],
                "retained": hits[s], "removed": 1 - hits[s],
                "matched_k_control_sha256": commitments[name],
                "matched_k_control_retained": control_hit,
            })
    if len(rows)-WARMUP != TEST_WINDOWS:
        raise AssertionError("evaluation-window drift")
    summary = {
        name: {
            "coalition": s, "candidate_count": frozen[s]["candidate_count"],
            "compression_rate_fraction": [DOMAIN - frozen[s]["candidate_count"], DOMAIN],
            "retained_targets": totals[s],
            "removed_targets": TEST_WINDOWS-totals[s],
            "retention_rate_fraction": [totals[s], TEST_WINDOWS],
            "matched_k_expected_retained": TEST_WINDOWS*frozen[s]["candidate_count"]/DOMAIN,
            "matched_k_control_retained": baseline_totals[name],
            "windows": ledger[name],
        } for name,s in arms.items()
    }
    return {
        "schema": "pl5-historical-static-walkforward-v3756-1",
        "provenance": "RETROSPECTIVE_CROSSCHECKED_TRANSCRIPTS_NOT_SOURCE_AUTHENTICATED",
        "input_hashes": EXPECTED_HASHES,
        "first_evaluated_issue": rows[WARMUP][0],
        "last_evaluated_issue": rows[-1][0],
        "historical_records": len(rows),
        "training_prefix_records": WARMUP,
        "evaluation_windows_crosschecked": TEST_WINDOWS,
        "source_html_archived": False,
        "independent_historical_timestamp": False,
        "frozen_rule_families": list(FAMILY_MASKS),
        "coalition_count": len(coalitions),
        "frozen_coalitions": frozen,
        "all_coalition_retained_targets": totals,
        "named_arms": summary,
        "historical_coverage_measured": True,
        "no_target_window_rule_fitting": True,
        "dynamic_rules_evaluated": False,
        "claim_of_superiority": False,
    }


class TestWalkforward(unittest.TestCase):
    def test_sources_and_window_separation(self):
        rows = verified_rows()
        self.assertEqual(len(rows),51)
        self.assertEqual(rows[WARMUP][0],"26275")
        self.assertEqual(rows[-1][0],"26294")

    def test_reject_modified_record(self):
        self.assertRaises(ValueError,parse_csv, PRIMARY, "0"*64)

    def test_bitmaps_independent_bruteforce(self):
        mask = masks()
        coalitions = all_coalitions(mask)
        self.assertEqual(len(coalitions),1024)
        for n in (0,1,12345,54321,99999):
            membership = sum(((m >> n)&1) << i for i,m in enumerate(mask))
            for subset in range(1024):
                self.assertEqual((coalitions[subset] >> n)&1,
                                 int(membership & subset == subset))

    def test_prefix_only_random_control(self):
        p = history_digest([("1","00001")])
        self.assertEqual(random_control(p,"2","arm",100,target=7),
                         random_control(p,"2","arm",100,target=99999))

    def test_full_historical_replay(self):
        r = run()
        self.assertEqual(len(r["named_arms"]),17)
        self.assertEqual(len(r["all_coalition_retained_targets"]),1024)
        for arm in r["named_arms"].values():
            self.assertEqual(len(arm["windows"]),20)
            self.assertEqual(arm["retained_targets"]+arm["removed_targets"],20)
            self.assertEqual(arm["candidate_count"],
                             r["frozen_coalitions"][arm["coalition"]]["candidate_count"])
        self.assertEqual(r["all_coalition_retained_targets"][0],20)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TestWalkforward)
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    report=run()
    raw=json.dumps(report,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as f:
            f.write(raw)
    compact={name:{
        "K":arm["candidate_count"],
        "retained":arm["retained_targets"],
        "matched_k_control":arm["matched_k_control_retained"],
        "expected":arm["matched_k_expected_retained"]}
        for name,arm in report["named_arms"].items()}
    print("V3756_REPORT_SHA256="+sha256(raw.encode()).hexdigest())
    print("V3756_SUMMARY_JSON="+json.dumps(compact,sort_keys=True))
