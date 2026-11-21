import subprocess
import sys
from pathlib import Path


def test_v371_imports_as_part_of_cumulative_package():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-c', 'import pailie5.operator_evolution_v371'],
        cwd=root, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
