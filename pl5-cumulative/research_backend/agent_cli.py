"""阶段二CLI。示例：python agent_cli.py --help。"""
import argparse
import json
from pathlib import Path
from pailie5.knowledge import KnowledgeBase
from pailie5.data import load_csv
from pailie5.research_agent import ResearchAgent
from pailie5.discovery import step_metrics

BASE=Path(__file__).parent

def main():
    p=argparse.ArgumentParser(description='排列五 V0.2 多智能体算法验证系统（研究用途）')
    p.add_argument('--db',type=Path,default=BASE/'runtime'/'knowledge.sqlite')
    sub=p.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import',help='验证并入库一个真实开奖CSV，不允许模糊号码和冲突覆盖')
    imp.add_argument('--csv',type=Path,required=True);imp.add_argument('--source',required=True)
    mir=sub.add_parser('fetch-community',help='显式获取社区镜像CSV（非官方），建议人工与体彩公告核对')
    mir.add_argument('--file',type=Path,help='离线使用已下载的镜像CSV（无需联网）')
    sub.add_parser('sources',help='查看导入来源与数字指纹')
    sub.add_parser('experiments',help='列出已封存实验')
    exp=sub.add_parser('research',help='预注册开发集实验并只打开一次封存测试集')
    exp.add_argument('--demo',action='store_true',help='使用本地合成数据演示（绝非真实开奖结果）')
    exp.add_argument('--count',type=int,default=1000)
    exp.add_argument('--dev-size',type=int,default=40)
    exp.add_argument('--holdout-size',type=int,default=40)
    exp.add_argument('--min-train',type=int,default=100)
    exp.add_argument('--window',type=int,default=500)
    exp.add_argument('--seed',type=int,default=42)
    exp.add_argument('--llm',action='store_true',help='可选调用OpenAI仅提供白名单参数提案，需自配API Key')
    exp.add_argument('--llm-model',default='gpt-5.5')
    exp.add_argument('--graph',choices=['auto','off','required'],default='auto')
    exp.add_argument('--output',type=Path,default=BASE/'runtime'/'last_report.json')
    args=p.parse_args()
    kb=KnowledgeBase(args.db)
    try:
        if args.command=='import':
            result=kb.import_csv(args.csv.read_bytes(),args.source)
            print(json.dumps(result.__dict__,ensure_ascii=False,indent=2))
        elif args.command=='fetch-community':
            from pailie5.sources import fetch_community_mirror, normalize_community_csv, COMMUNITY_MIRROR_URL
            data=(normalize_community_csv(args.file.read_bytes()) if args.file else fetch_community_mirror())
            result=kb.import_csv(data,source_name='第三方社区镜像：'+COMMUNITY_MIRROR_URL,
                                 kind='community_unverified')
            print(json.dumps(result.__dict__,ensure_ascii=False,indent=2))
            print('【警告】数据来自第三方自动同步镜像，不等于官方认证。请人工与中国体彩网公告交叉核验。')
        elif args.command=='sources':
            print(json.dumps(kb.sources(),ensure_ascii=False,indent=2))
        elif args.command=='experiments':
            print(json.dumps(kb.experiments(),ensure_ascii=False,indent=2))
        elif args.command=='research':
            if args.demo:
                print('注意：当前研究使用随机合成数据，不代表真实历史表现。')
                # 演示用的知识库也会封存，一次运行后重复运行应选择全新数据库路径。
                raw=(BASE/'data'/'synthetic_demo.csv').read_bytes()
                draws=load_csv(raw,is_demo=True)
            else:
                draws=kb.merged_draws()
            agent=ResearchAgent(draws,kb)
            report=agent.run(count=args.count,dev_size=args.dev_size,
                             holdout_size=args.holdout_size,window=args.window,
                             min_train=args.min_train,seed=args.seed,llm=args.llm,
                             llm_model=args.llm_model,use_langgraph=args.graph)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print('报告:',args.output.resolve())
            print('实验:',report['experiment_id'],'开发阶段选择:',report['preregistration']['chosen'])
            print('封存验证:',report['holdout'])
    finally:
        kb.close()

if __name__=='__main__':
    main()
