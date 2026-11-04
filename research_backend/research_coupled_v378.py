"""Reproduce a locked, bounded V3.7.8 synthetic coupling experiment.

Usage: python research_coupled_v378.py --protocol ../docs/v378/protocol.json --output ../runs/v378.json
The runner will not overwrite an existing output file.
"""
import argparse
import json
from pathlib import Path
from pailie5.coupled_study_v378 import run_registered


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text(encoding='utf-8'))
    result=run_registered(protocol)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,sort_keys=True)
        handle.write('\n')
    print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':
    main()
