"""V3.7.67: isolated-process cold output and Python allocation audit.
INTERNAL/AI_AUTHORED. Fixed full signed queries; no historical data accessed.
"""
from time import perf_counter_ns
START = perf_counter_ns()
import gc
import hashlib
import json
import platform
import statistics
import struct
import subprocess
import sys
import tracemalloc
from pathlib import Path

from refined_atom_floor_v3762 import freeze, partition, DOMAIN, CAP, digest

STRATEGIES = ("fixed", "bitmap", "packed")
COLD_REPEATS = 3
WARM_REPEATS = 7
LEDGER = "ce3bf2c3ab1e336334420357320a613e6d334dcfc04cec423fd24f12834735f6"


def encode(sig, mask):
    # Canonical binary output: uint16 signature, uint16 count, sorted
    # uint32 identities, all little endian; no platform-native encoding.
    out = bytearray(struct.pack("<HH", sig, mask.bit_count()))
    while mask:
        low = mask & -mask
        out.extend(struct.pack("<I", low.bit_length()-1))
        mask ^= low
    return bytes(out)


def fixed_runner(raw, size):
    full = (1 << size)-1
    pairs = tuple((full ^ m, m) for m in raw)
    def run(sig):
        mask = full
        for j, pair in enumerate(pairs):
            mask &= pair[(sig >> j) & 1]
        return mask
    return run


def setup(strategy, raw, size, queries):
    if strategy == "fixed":
        run = fixed_runner(raw, size)
        return lambda sig: encode(sig, run(sig))
    atoms, _ = partition(raw, size)
    if strategy == "bitmap":
        return lambda sig: encode(sig, atoms[sig])
    if strategy == "packed":
        cache = {sig: encode(sig, atoms[sig]) for sig in queries}
        return cache.__getitem__
    raise ValueError(strategy)


def batch(run, queries):
    return b"".join(run(sig) for sig in queries)


def inventory():
    _, raw, stages = freeze()
    queries = tuple(s for s,k in enumerate(stages[12][0]) if 0 < k <= CAP)
    assert len(raw) == 12 and len(queries) == 893
    return raw, queries


def oracle():
    # Independent fixed intersections and the previous frozen mask ledger.
    raw, queries = inventory()
    run = fixed_runner(raw, DOMAIN)
    h = hashlib.sha256()
    expected = bytearray()
    for sig in queries:
        m = run(sig)
        h.update(sig.to_bytes(2, "little"))
        h.update(bytes.fromhex(digest(m)))
        # Independent enumeration by byte positions, not low-bit extraction.
        ids = [i*8+j for i,b in enumerate(m.to_bytes(DOMAIN//8,"little"))
               if b for j in range(8) if b & (1<<j)]
        assert 0 < len(ids) <= CAP
        expected.extend(struct.pack("<HH",sig,len(ids)))
        expected.extend(struct.pack("<%dI" % len(ids),*ids))
    assert h.hexdigest() == LEDGER
    assert len(expected) == 4*(893+16244)
    return hashlib.sha256(expected).hexdigest(), len(expected)


def toy():
    raw = (0b10101010,0b11001100,0b10101010)
    atoms,_ = partition(raw,8)
    queries = tuple(range(8))
    expected = b"".join(struct.pack("<HH",s,a.bit_count())+
        b"".join(struct.pack("<I",i) for i in range(8) if (a>>i)&1)
        for s,a in enumerate(atoms))
    for strategy in STRATEGIES:
        assert batch(setup(strategy,raw,8,queries),queries) == expected


def worker(strategy, mode):
    raw,queries = inventory()
    gc.collect()
    if mode == "memory":
        # Trace strategy setup + first output only; shared rule construction
        # and interpreter/native allocator memory are intentionally excluded.
        tracemalloc.start()
        run = setup(strategy,raw,DOMAIN,queries)
        retained, setup_peak = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        payload = batch(run,queries)
        with_output, query_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result = dict(retained_setup_bytes=retained, setup_peak_bytes=setup_peak,
                      first_output_current_bytes=with_output,
                      first_output_peak_bytes=query_peak)
    else:
        t = perf_counter_ns()
        run = setup(strategy,raw,DOMAIN,queries)
        setup_ns = perf_counter_ns()-t
        t = perf_counter_ns()
        payload = batch(run,queries)
        first_ns = perf_counter_ns()-t
        result = dict(setup_ns=setup_ns, first_output_ns=first_ns,
                      through_first_output_ns=perf_counter_ns()-START)
        if mode == "warm":
            expected = hashlib.sha256(payload).digest()
            samples = []
            for _ in range(WARM_REPEATS):
                t = perf_counter_ns()
                payload = batch(run,queries)
                samples.append(perf_counter_ns()-t)
                assert hashlib.sha256(payload).digest() == expected
            result["warm_output_ns"] = samples
            result["median_warm_output_ns"] = int(statistics.median(samples))
    result.update(output_sha256=hashlib.sha256(payload).hexdigest(),
                  output_bytes=len(payload))
    return result


def fresh(strategy,mode,expected):
    # Cold process wall includes Python launch, imports, freeze, setup,
    # first serialization, checksum, tiny metrics IPC and interpreter exit.
    # The actual candidate payload is built in memory, not sent over IPC.
    t = perf_counter_ns()
    p = subprocess.run([sys.executable,str(Path(__file__).resolve()),
                        "--worker",strategy,mode],capture_output=True,
                       text=True,check=True,timeout=90)
    wall = perf_counter_ns()-t
    row = json.loads(p.stdout)
    assert (row["output_sha256"],row["output_bytes"]) == expected
    if mode == "cold":
        row["fresh_process_wall_ns"] = wall
    return row


def audit():
    toy()
    expected = oracle()
    rows = {s:{"cold":[] } for s in STRATEGIES}
    for i in range(COLD_REPEATS):
        for s in STRATEGIES[i:]+STRATEGIES[:i]:
            rows[s]["cold"].append(fresh(s,"cold",expected))
    for s in STRATEGIES:
        rows[s]["warm"] = fresh(s,"warm",expected)
        rows[s]["memory"] = fresh(s,"memory",expected)
        rows[s]["median_fresh_process_wall_ns"] = int(statistics.median(
            x["fresh_process_wall_ns"] for x in rows[s]["cold"]))
    return dict(schema="pl5-bitmap-output-cost-v3767-1",
                source="INTERNAL/AI_AUTHORED", platform=platform.platform(),
                python=platform.python_version(), domain=DOMAIN, cap=CAP,
                query_count=893, output_sha256=expected[0],
                output_bytes=expected[1], candidate_ledger_sha256=LEDGER,
                candidate_membership_preserved=True,
                historical_coverage_measured=False, cold_repeats=COLD_REPEATS,
                warm_repeats=WARM_REPEATS, memory_repeats=1, strategies=rows,
                limitations=["complete frozen signatures only",
                    "memory is incremental Python tracemalloc, not process RSS",
                    "separate memory pass; no traced timing comparisons",
                    "cold process wall includes common freeze and process exit",
                    "binary output built in memory, no network or disk transfer",
                    "packed cache precomputes output and is restricted to fixed workload",
                    "no timing gates or cross-machine speed ranking"])


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2],sys.argv[3]),sort_keys=True))
    else:
        print("V3767_OUTPUT_COST_JSON="+json.dumps(audit(),sort_keys=True))
