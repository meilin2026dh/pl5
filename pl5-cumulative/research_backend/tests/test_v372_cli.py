import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_v372_cli_exists():
    assert (ROOT / 'research_v372.py').is_file()


def test_cli_fits_and_evaluates_without_refitting(tmp_path):
    training = tmp_path / 'train.json'
    heldout = tmp_path / 'heldout.json'
    training.write_text(json.dumps([[a,b,(a+b)%10] for a in range(10) for b in range(7)]))
    heldout.write_text(json.dumps([[a,b,(a+b)%10] for a in range(10) for b in range(7,10)]))
    out = tmp_path / 'fit'
    run = subprocess.run([sys.executable, 'research_v372.py', 'fit', '--input', str(training),
                          '--output', str(out), '--max-evaluations', '500'], cwd=ROOT,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert (out/'operator.json').is_file()
    verify = subprocess.run([sys.executable, 'research_v372.py', 'evaluate',
                             '--operator', str(out/'operator.json'), '--input', str(heldout)],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert verify.returncode == 0, verify.stderr
    result = json.loads(verify.stdout)
    assert result['errors'] == 0 and result['count'] == 30
    assert result['refitted'] is False


def test_cli_rejects_invalid_cells_and_existing_output(tmp_path):
    bad = tmp_path / 'bad.json'
    bad.write_text('[[0,0,17]]')
    run = subprocess.run([sys.executable, 'research_v372.py', 'fit', '--input', str(bad),
                          '--output', str(tmp_path/'out')], cwd=ROOT,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode != 0
    assert not (tmp_path/'out'/'operator.json').exists()


def test_demo_has_explicit_synthetic_labels_and_real_files(tmp_path):
    out = tmp_path/'demo'
    run = subprocess.run([sys.executable, 'research_v372.py', 'demo', '--output', str(out),
                          '--max-evaluations', '600'], cwd=ROOT,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    report = json.loads((out/'report.json').read_text())
    assert report['data_type'] == 'synthetic_operation_table'
    assert report['holdout']['count'] == 30
    assert report['search']['operator']['production_enabled'] is False
