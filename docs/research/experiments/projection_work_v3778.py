"""V3.7.78: deterministic projection-work proxy audit.

INTERNAL/AI_AUTHORED. Fixed static partitions and archived timing only.
No history, fitting, retained-set selection, or new rule masks.
"""
from hashlib import sha256
from statistics import median
import json
import unittest
import numpy as np
from scipy.stats import kendalltau, spearmanr

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from projection_cost_v3776 import project
from robust_projection_v3777 import EVIDENCE

SOURCE_HEAD = "0ce2d79df6af3be601d0c03445dd8dd9dc088728"


def normalized_evidence_hash(raw):
    """Normalize actual CRLF line endings; preserve literal JSON escapes."""
    return sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def work(occupied, s):
    """Each input atom incurs one AND, lookup, addition and assignment.
    Distinguish logical new-key assignments from existing-key updates.
    These are semantic counts, not CPU instructions or hash probes.
    """
    groups = project(occupied, s)
    g = len(groups)
    m = len(occupied)
    assert 1 <= g <= m
    return m, g, m-g


def agreement(x, y):
    """Count ordering agreement, disagreement and ties explicitly."""
    x, y = np.asarray(x, dtype=np.int64), np.asarray(y, dtype=np.int64)
    assert len(x) == len(y)
    i, j = np.triu_indices(len(x), k=1)
    a, b = np.sign(x[i]-x[j]), np.sign(y[i]-y[j])
    both = (a != 0) & (b != 0)
    c = int(np.sum(both & (a == b)))
    d = int(np.sum(both & (a != b)))
    xt = int(np.sum((a == 0) & (b != 0)))
    yt = int(np.sum((a != 0) & (b == 0)))
    bt = int(np.sum((a == 0) & (b == 0)))
    assert c+d+xt+yt+bt == len(i)
    if len(set(x)) > 1 and len(set(y)) > 1:
        tau = (c-d)/((c+d+xt)*(c+d+yt))**0.5
        assert abs(tau - kendalltau(x,y).statistic) < 1e-12
        rho = float(spearmanr(x,y).statistic)
    else:
        tau = rho = None
    return {"pairs":len(i),"concordant":c,"discordant":d,
            "proxy_ties_only":xt,"time_ties_only":yt,"both_tied":bt,
            "kendall_tau_b":tau,"spearman_rho":rho,
            "concordant_fraction":c/(c+d) if c+d else None}


def audit():
    raw_evidence = EVIDENCE.read_bytes()
    data = json.loads(raw_evidence)
    assert data["schema"] == "pl5-projection-cost-v3776-evidence-1"
    names, raw, _ = freeze()
    n = len(raw)
    assert n == 12
    _, counts = partition(raw, DOMAIN)
    occupied = tuple((s,k) for s,k in enumerate(counts) if k)
    ids = list(range(1,1<<n))
    records = [work(occupied,s) for s in ids]
    # Reconstruct the exact V3.7.76 projection ledger; no timing measured here.
    ledger = sha256()
    for s, (m,g,u) in zip(ids,records):
        groups = project(occupied,s)
        assert len(groups)==g and m==g+u and sum(groups.values())==DOMAIN
        assert g==len({v&s for v,k in occupied})
        ledger.update(json.dumps([s,sorted(groups.items())],
                      separators=(",",":")).encode())
    projection_hash = ledger.hexdigest()
    results = []
    for p in data["platforms"]:
        r = p["report"]
        assert r["domain"]==DOMAIN and r["rule_names"]==list(names)
        assert r["rule_mask_sha256"]==[digest(m) for m in raw]
        assert r["projection_ledger_sha256"]==projection_hash
        assert r["seeds"]==[760,761,762,763,764]
        t = p["timings_by_subset"]
        assert len(t)==len(ids) and all(len(v)==5 and
            all(type(x) is int and x>0 for x in v) for v in t)
        rows=[]
        for k in range(1,n+1):
            ix=[s-1 for s in ids if s.bit_count()==k]
            g=[records[i][1] for i in ix]
            # Fixed directional hypothesis: more output groups -> higher cost.
            # No fit or direction change on these measurements.
            times=[[t[i][j] for i in ix] for j in range(5)]
            med=[int(median(t[i])) for i in ix]
            rows.append({"rule_budget":k,"subsets":len(ix),
                "groups_min":min(g),"groups_max":max(g),
                "distinct_group_counts":len(set(g)),
                "median_time_agreement":agreement(g,med),
                "repeat_agreement":[agreement(g,v) for v in times]})
        results.append({"platform":r["platform"],"rows":rows})
    assert len(results)==2
    return {"schema":"pl5-projection-work-v3778-1","source":"INTERNAL/AI_AUTHORED",
        "source_head":SOURCE_HEAD,"evidence_normalized_sha256":
            normalized_evidence_hash(raw_evidence),
        "projection_ledger_sha256":projection_hash,
        "rule_mask_sha256":[digest(m) for m in raw],
        "scan_steps_per_subset":len(occupied),
        "records_columns":["subset","scan_steps","new_keys","existing_updates"],
        "records_sha256":sha256(json.dumps([[s,*v] for s,v in zip(ids,records)],
              separators=(",",":")).encode()).hexdigest(),
        "platforms":results,
        "limitations":["archived development measurements, not independent validation",
          "scan steps constant; cannot rank subsets by scan count",
          "new keys and updates are complementary, not independent predictors",
          "rank association only, not causal or calibrated elapsed-time model",
          "ties retained; no pooled cross-budget or cross-platform timing comparisons",
          "cached projection only; no complete execution cost or historical coverage"]}


class Tests(unittest.TestCase):
    def test_evidence_line_endings(self):
        lf = b'{"escaped":"\\r\\n"}\n'
        crlf = lf.replace(b"\n", b"\r\n")
        self.assertNotEqual(sha256(lf).hexdigest(), sha256(crlf).hexdigest())
        self.assertEqual(normalized_evidence_hash(lf), sha256(lf).hexdigest())
        self.assertEqual(normalized_evidence_hash(crlf), sha256(lf).hexdigest())
        self.assertNotEqual(normalized_evidence_hash(lf),
                            normalized_evidence_hash(lf.replace(b"\\r\\n", b"\\n")))

    def test_work(self):
        occupied=((0,2),(1,3),(2,4),(3,1))
        self.assertEqual(work(occupied,0),(4,1,3))
        self.assertEqual(work(occupied,1),(4,2,2))
        self.assertEqual(work(occupied,3),(4,4,0))

    def test_agreement(self):
        self.assertAlmostEqual(agreement([1,2,3],[3,2,1])["kendall_tau_b"],-1)
        self.assertAlmostEqual(agreement([1,2,2],[1,2,2])["kendall_tau_b"],1)
        self.assertIsNone(agreement([1,1],[1,2])["kendall_tau_b"])
        self.assertEqual(agreement([1,1],[1,2])["proxy_ties_only"],1)
        self.assertEqual(agreement([1],[1])["pairs"],0)
        self.assertEqual(agreement([1,2,3],[1,1,2])["time_ties_only"],1)

    def test_full(self):
        r=audit()
        for p in r["platforms"]:
            self.assertEqual(sum(x["subsets"] for x in p["rows"]),4095)
            self.assertEqual(len(p["rows"]),12)
            self.assertTrue(all(len(x["repeat_agreement"])==5 for x in p["rows"]))
        self.__class__.result=r


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3778_WORK_JSON="+json.dumps(Tests.result,sort_keys=True,allow_nan=False))
