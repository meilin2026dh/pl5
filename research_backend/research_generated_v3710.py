"""Reproducible V3.7.10 synthetic study: predeclared cases only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.generated_study_v3710 import protocol, run_predeclared


def main():
    ap=argparse.ArgumentParser(description='bounded train-only V3.7.10 mathematical experiments')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',default=[8811,8812,8813,8814,8815,8816,8817,8818])
    args=ap.parse_args()
    settings=protocol(tuple(args.seeds))
    result=run_predeclared(settings)
    args.output.mkdir(parents=True,exist_ok=True)
    for name,value in [('protocol.json',settings),('results.json',result)]:
        path=args.output/name
        path.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False,sort_keys=True))

if __name__=='__main__': main()
