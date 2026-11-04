"""PL5 V2.5 autonomous bounded representation research CLI. No network and no bet API."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.representation_v25 import propose, audit, study
from research_v24 import read_history
from pailie5.representation_registry_v25 import cycle as run_cycle, status as inventory_status


def main(argv=None):
    ap=argparse.ArgumentParser(description='PL5 V2.5 创造新空间、去冗余、严格时间留出研究')
    ap.add_argument('command',choices=['propose','study','demo','cycle','status'])
    ap.add_argument('--history',type=Path,help='已核验官方开奖结果CSV，含number列')
    ap.add_argument('--db',type=Path,default=Path('runtime/representation_v25.sqlite'))
    ap.add_argument('--seed',type=int,default=20261102)
    ap.add_argument('--count',type=int,default=24)
    ap.add_argument('--test-periods',type=int,default=30)
    ap.add_argument('--alpha',type=float,default=100.)
    ap.add_argument('--report',type=Path)
    ap.add_argument('--numbers',type=Path,help='可选：导出实验性Top100和随机对照')
    a=ap.parse_args(argv)
    if a.command=='cycle':
        out=run_cycle(a.db,base_seed=a.seed,count=a.count)
    elif a.command=='status':
        out=inventory_status(a.db)
    elif a.command=='propose':
        out={'status':'engineering_only','seed':a.seed,'candidate_audit':audit(propose(a.seed,a.count))}
    else:
        if a.command=='study':
            if a.history is None:ap.error('研究必须提供显式历史文件；不把演示数据当官方')
            history=read_history(a.history)
        else:
            history=[f'{(7919*i+17*i*i)%100000:05d}' for i in range(160)]
        out=study(history,seed=a.seed,count=a.count,test_periods=a.test_periods,alpha=a.alpha)
        out['source']='synthetic_demo' if a.command=='demo' else str(a.history)
    raw=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(raw+'\n',encoding='utf-8')
        print('报告：',a.report)
    else:
        print(raw[:12000]+ ('\n...内容已截断，请指定--report' if len(raw)>12000 else ''))
    if a.numbers:
        if 'next_draw_exploratory_top100' not in out:raise ValueError('只有demo/study支持导出号码')
        a.numbers.parent.mkdir(parents=True,exist_ok=True)
        a.numbers.write_text('number,group\n'+'\n'.join(f'{n},exploratory' for n in out['next_draw_exploratory_top100'])+'\n'
            +'\n'.join(f'{n},random_control' for n in out['next_draw_random_control_100'])+'\n',encoding='utf-8-sig')
        print('双组候选：',a.numbers)

if __name__=='__main__':main()
