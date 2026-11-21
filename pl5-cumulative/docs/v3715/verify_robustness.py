"""Independent PL5 membership oracle for V3.7.15 supplementary seed experiments."""
import json
from pathlib import Path
import sys
import time
import hashlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research_backend'))
from benchmark_high_throughput_v3714 import _rules
from pailie5.basic_filters import apply_basic_filters
from pailie5.high_throughput_v3714 import ExactFilterEngine, mask_from_bitmap
import numpy as np

p=Path(__file__).with_name('robustness_results.json')
d=json.loads(p.read_text('utf-8'))
rules=_rules()
rule_by_name=dict(rules)
engine=ExactFilterEngine()
for name,rule in rules: engine.add_basic(name,rule)
failed=[]
started=time.perf_counter()
for idx,r in enumerate(d['results']):
    names=r['selected_rules']
    if len(names)!=len(set(names)) or any(n not in rule_by_name for n in names):
        failed.append({'row':idx,'reason':'invalid names'}); continue
    legacy=apply_basic_filters([rule_by_name[n] for n in names])
    acc=(1<<100000)-1
    for name in names: acc &= engine._compile(name)
    bitmap=np.flatnonzero(mask_from_bitmap(acc))
    if not np.array_equal(legacy,bitmap) or len(legacy)!=r['survivors']:
        failed.append({'row':idx,'reason':'membership or count disagreement'})
report={'trials':len(d['results']), 'oracle_comparisons':len(d['results']), 'mismatch_count':len(failed), 'failure_examples':failed[:10],
        'elapsed_seconds':round(time.perf_counter()-started,6),
        'source_results_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'oracle':'legacy apply_basic_filters vs frozen static bitmap full 100000-member array',
        'uses_real_lottery_draws':False}
out=Path(__file__).with_name('robustness_oracle_verification.json')
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
if failed: raise SystemExit(1)
