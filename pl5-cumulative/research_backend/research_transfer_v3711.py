"""Run finite preregistered V3.7.11 synthetic protocol and write local evidence."""
import argparse
import json
from pathlib import Path
from pailie5.transfer_study_v3711 import protocol,run_study


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',default=[9541,9542,9543,9544,9545,9546])
    args=ap.parse_args()
    p=protocol(tuple(args.seeds))
    result=run_study(p)
    args.output.mkdir(parents=True,exist_ok=True)
    for filename,value in [('protocol.json',p),('results.json',result)]:
        (args.output/filename).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],sort_keys=True,ensure_ascii=False))

if __name__=='__main__':main()
