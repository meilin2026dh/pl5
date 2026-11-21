"""V0.4 命令行：离线运行多空间研究与安慰剂验证。"""
import argparse
import json
from pathlib import Path
import pandas as pd

from pailie5.data import load_csv
from pailie5.multispace import multi_space_study, competition_backtest
from pailie5.mapping_robustness import robustness_study
from pailie5.space_mapping import SPACES


def main() -> None:
    p=argparse.ArgumentParser(description='PL5 V0.4 多空间过滤竞争/映射稳健性实验')
    p.add_argument('--csv',required=True,help='已核验的官方CSV（或者合成演示文件）')
    p.add_argument('--demo',action='store_true',help='标记为非官方演示数据')
    p.add_argument('--out',default='runtime/v04',help='输出前缀')
    p.add_argument('--holdout',type=int,default=15)
    p.add_argument('--top-k',type=int,default=1000)
    p.add_argument('--variants',type=int,default=5)
    p.add_argument('--competition-periods',type=int,default=12)
    args=p.parse_args()
    rows=load_csv(Path(args.csv).read_bytes(),is_demo=args.demo)
    history=rows.frame['number'].tolist()
    chosen={'pl5':('sum','span','odd_count'),
            'pick23_6':('sum','span','odd_count'),
            'pick41_4':('sum','span','odd_count'),
            'ternary11':('three_count','one_count','switch_count')}
    study=multi_space_study(history,chosen)
    prefix=Path(args.out)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    study.table.to_csv(str(prefix)+'_rank100k.csv',index=False,encoding='utf-8-sig')
    study.rule_table.to_csv(str(prefix)+'_rules.csv',index=False,encoding='utf-8-sig')
    output={'metadata':study.metadata,'competition':study.competition,
            'warnings':rows.warnings,'is_demo':rows.is_demo}
    if len(history)>=42:
        output['rolling_competition']=competition_backtest(history,chosen,max_periods=args.competition_periods)
    if len(history)>=42:
        output['mapping_robustness']=robustness_study(
            history,'pick23_6',('sum','span'),variant_count=args.variants,
            holdout=args.holdout,top_k=args.top_k)
    else:
        output['mapping_robustness']='历史不足42期，跳过对照验证'
    path=str(prefix)+'_report.json'
    Path(path).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'rank_file':str(prefix)+'_rank100k.csv',
                      'rules_file':str(prefix)+'_rules.csv',
                      'report_file':path,'rules':study.metadata['accepted_rules'],
                      'source_is_demo':rows.is_demo},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
