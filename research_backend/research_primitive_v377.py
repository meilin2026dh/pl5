"""Reproduce a frozen V3.7.7 protocol; do not overwrite prior research."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.primitive_study_v377 import run_predeclared


def main():
    p = argparse.ArgumentParser(description='V3.7.7 bounded synthetic primitive research')
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error(f'result already exists: {args.output}; choose a new path')
    if args.protocol.stat().st_size > 65536:
        p.error('protocol file too large')
    settings = json.loads(args.protocol.read_text(encoding='utf8'))
    evidence = run_predeclared(settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(evidence['summary'], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
