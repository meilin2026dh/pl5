"""V3.7.77: interval dominance for uncertain projection cost.
INTERNAL/AI_AUTHORED. Replay archived V3.7.76 measurements only.
No new timing, historical records, rule fitting or production changes.
"""
from hashlib import sha256
from pathlib import Path
from statistics import median
import json
import unittest
import numpy as np

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies
from static_pareto_v3775 import objectives, skyline

EVIDENCE = Path(__file__).with_name("projection_cost_v3776_evidence.json")
SOURCE_HEAD = "dfd6ec6648b3cfe013f181fd33543f4acf582d41"


def robust_dominates(a, b):
    # Coordinates: subset, negative information, redundancy, lower, upper.
    return (a[1] <= b[1] and a[2] <= b[2] and a[4] <= b[3]
            and (a[1] < b[1] or a[2] < b[2] or a[4] < b[3]))


def interval_skyline(rows):
    # Any strict robust dominator precedes its target in this order.
    # Transitivity permits retaining only undominated witnesses.
    ordered = sorted(rows, key=lambda r: (r[4], r[2], r[1], r[0]))
    front, rejected = [], {}
    for row in ordered:
        w = next((p for p in front if robust_dominates(p, row)), None)
        if w is None:
            front.append(row)
        else:
            rejected[row[0]] = w[0]
    return sorted(front), rejected


def reference(rows):
    # Independent dense pairwise check; only within a rule-count stratum.
    v = np.asarray(rows, dtype=np.int64)
    info = v[:, 1, None] - v[None, :, 1]
    red = v[:, 2, None] - v[None, :, 2]
    cost = v[:, 4, None] - v[None, :, 3]
    dom = ((info <= 0) & (red <= 0) & (cost <= 0)
           & ((info < 0) | (red < 0) | (cost < 0)))
    return {r[0] for r, rejected in zip(rows, dom.any(axis=0)) if not rejected}


def fit(pool, timings, indices):
    med = []
    intervals = []
    for s, i, r, _ in pool:
        t = [timings[s][j] for j in indices]
        med.append((s, i, r, int(median(t))))
        intervals.append((s, i, r, min(t), max(t)))
    mf, mw = skyline(med)
    rf, rw = interval_skyline(intervals)
    m = {x[0] for x in mf}
    f = {x[0] for x in rf}
    assert f == reference(intervals)
    assert m <= f
    by_id = {x[0]: x for x in intervals}
    assert len(f) + len(rw) == len(pool)
    assert all(w in f and robust_dominates(by_id[w], by_id[s])
               for s, w in rw.items())
    # Every observed repeat frontier must be preserved.
    for j in indices:
        sample = [(s, i, r, timings[s][j]) for s, i, r, _ in pool]
        sf, _ = skyline(sample)
        assert {x[0] for x in sf} <= f
    return m, mw, f, rw


def validate(witnesses, pool, timings, indices):
    """Evaluate fixed training witnesses, without reselection on held-out costs."""
    by_id = {x[0]: x for x in pool}
    failed = []
    comparisons = 0
    failed_comparisons = 0
    for s, w in sorted(witnesses.items()):
        bad = False
        for j in indices:
            a, b = by_id[w], by_id[s]
            ta, tb = timings[w][j], timings[s][j]
            ok = (a[1] <= b[1] and a[2] <= b[2] and ta <= tb
                  and (a[1] < b[1] or a[2] < b[2] or ta < tb))
            comparisons += 1
            failed_comparisons += int(not ok)
            bad |= not ok
        if bad:
            failed.append(s)
    return {"rejected": len(witnesses), "comparisons": comparisons,
            "failed_comparisons": failed_comparisons,
            "failed_witnesses": failed,
            "witnesses": sorted(witnesses.items())}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 1.0


def replay(base, a, b, old_rows):
    rows = []
    for old in old_rows:
        k = old["rule_budget"]
        pool = [r for r in base[1:] if r[0].bit_count() == k]
        m, mw, f, rw = fit(pool, a, (0, 1, 2))
        all_m, _, all_f, all_rw = fit(pool, a, (0, 1, 2, 3, 4))
        assert all_m == set(old["median_frontier"])
        assert set(old["stable_all_repeat_frontier"]) <= all_f
        assert len(pool) == old["enumerated"]
        rows.append({"rule_budget": k, "enumerated": len(pool),
                     "train_median_frontier": sorted(m),
                     "train_interval_frontier": sorted(f),
                     "full_median_frontier": sorted(all_m),
                     "full_interval_frontier": sorted(all_f),
                     "full_interval_witnesses": sorted(all_rw.items()),
                     "same_runner_median": validate(mw, pool, a, (3, 4)),
                     "same_runner_interval": validate(rw, pool, a, (3, 4)),
                     "other_runner_median": validate(mw, pool, b, tuple(range(5))),
                     "other_runner_interval": validate(rw, pool, b, tuple(range(5)))})
    return rows


def audit():
    payload = EVIDENCE.read_bytes()
    archived = json.loads(payload)
    assert archived["schema"] == "pl5-projection-cost-v3776-evidence-1"
    names, raw, _ = freeze()
    _, counts = partition(raw, DOMAIN)
    base = objectives(subset_entropies(counts, len(raw)), (1,) * len(raw))
    platforms = archived["platforms"]
    assert len(platforms) == 2
    timing = []
    for p in platforms:
        r = p["report"]
        assert r["domain"] == DOMAIN and r["rule_names"] == list(names)
        assert r["rule_mask_sha256"] == [digest(m) for m in raw]
        assert r["seeds"] == [760, 761, 762, 763, 764]
        t = p["timings_by_subset"]
        assert len(t) == len(base)-1 == 4095
        assert all(len(v) == 5 and all(type(x) is int and x > 0 for x in v) for v in t)
        timing.append({s: v for s, v in enumerate(t, 1)})
    assert platforms[0]["report"]["projection_ledger_sha256"] == platforms[1]["report"]["projection_ledger_sha256"]
    results = [replay(base, timing[i], timing[1-i], p["report"]["rows"])
               for i, p in enumerate(platforms)]
    cross = []
    for x, y in zip(*results):
        cross.append({"rule_budget": x["rule_budget"],
                      "median_jaccard": jaccard(set(x["full_median_frontier"]), set(y["full_median_frontier"])),
                      "interval_jaccard": jaccard(set(x["full_interval_frontier"]), set(y["full_interval_frontier"])),
                      "interval_frontier_sizes": [len(z["full_interval_frontier"]) for z in (x,y)]})
    summary = []
    for p, rows in zip(platforms, results):
        totals = {}
        for key in ("same_runner_median", "same_runner_interval", "other_runner_median", "other_runner_interval"):
            totals[key] = {k: sum(r[key][k] for r in rows)
                           for k in ("rejected", "comparisons", "failed_comparisons")}
            totals[key]["failed_witnesses"] = sum(len(r[key]["failed_witnesses"]) for r in rows)
        summary.append({"platform": p["report"]["platform"], "totals": totals,
                        "full_median_size": sum(len(r["full_median_frontier"]) for r in rows),
                        "full_interval_size": sum(len(r["full_interval_frontier"]) for r in rows)})
    return {"schema": "pl5-robust-projection-v3777-1", "source": "INTERNAL/AI_AUTHORED",
            "source_head": SOURCE_HEAD, "evidence_sha256": sha256(payload).hexdigest(),
            "rule_mask_sha256": [digest(m) for m in raw],
            "train_indices": [0,1,2], "same_runner_evaluation_indices": [3,4],
            "summary": summary, "cross_platform": cross, "rows": results,
            "limitations": ["retrospective replay of already observed evidence, not independent validation",
              "intervals are observed extrema, not statistical confidence bounds",
              "larger frontier may mechanically improve Jaccard; report pruning and witness failures together",
              "fixed witness, not all pairwise relations; other runner compares within-run costs only",
              "cached projection cost only, no end-to-end cost or historical coverage"]}


class Tests(unittest.TestCase):
    def test_overlap_and_strict_ties(self):
        rows = [(1,-4,1,8,12),(2,-3,1,10,15),(3,-3,1,12,20),
                (4,-4,1,8,12),(5,-4,1,12,12)]
        f, w = interval_skyline(rows)
        self.assertEqual({r[0] for r in f}, {1,2,4,5})
        self.assertEqual(set(w), {3})
        self.assertEqual({r[0] for r in f}, reference(rows))

    def test_holdout_failure(self):
        pool = [(1,-4,1,1),(2,-3,1,1)]
        t = {1:[1,1,1,3,1],2:[2,2,2,2,2]}
        _, _, _, rw = fit(pool,t,(0,1,2))
        self.assertEqual(rw,{2:1})
        self.assertEqual(validate(rw,pool,t,(3,4))["failed_comparisons"],1)

    def test_full(self):
        r = audit()
        self.assertEqual(len(r["cross_platform"]),12)
        for s, rows in zip(r["summary"],r["rows"]):
            self.assertEqual(sum(x["enumerated"] for x in rows),4095)
            self.assertGreaterEqual(s["full_interval_size"],s["full_median_size"])
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    r = Tests.result
    print("V3777_ROBUST_JSON=" + json.dumps({k:v for k,v in r.items() if k != "rows"},sort_keys=True))
    for i, rows in enumerate(r["rows"]):
        for row in rows:
            print("V3777_WITNESSES_P"+str(i)+"_K"+str(row["rule_budget"])+"="+json.dumps(row,separators=(",",":")))
