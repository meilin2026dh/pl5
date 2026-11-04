"""Reproduce the deterministic V3.7.12 finite synthetic study."""
from pathlib import Path
import argparse,json
from pailie5.template_study_v3712 import protocol,run_study


def main():
    parser=argparse.ArgumentParser(description='PL5 V3.7.12 bounded cross-template synthetic transfer')
    parser.add_argument('--output',type=Path,default=Path('..')/'runs'/'v3712')
    args=parser.parse_args()
    p=protocol()
    result=run_study(p)
    args.output.mkdir(parents=True,exist_ok=True)
    for name,record in (('protocol.json',p),('results.json',result)):
        (args.output/name).write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,
                                                 indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],sort_keys=True,ensure_ascii=False))

if __name__=='__main__':main()
