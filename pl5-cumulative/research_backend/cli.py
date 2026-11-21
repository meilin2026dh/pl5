"""命令行运行，适合无人值守批处理和CI：uv run python cli.py --help。"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from pailie5.data import load_csv
from pailie5.agents import ResearchWorkflow


def main() -> None:
    p = argparse.ArgumentParser(description='排列五研究型多角色过滤实验系统')
    p.add_argument('--csv', type=Path, default=Path(__file__).parent/'data'/'synthetic_demo.csv')
    p.add_argument('--count', type=int, default=1000)
    p.add_argument('--model', choices=('positional','pairwise','ensemble','random'), default='ensemble')
    p.add_argument('--test-size', type=int, default=80)
    p.add_argument('--window', type=int, default=500)
    p.add_argument('--min-train', type=int, default=100)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--no-gate', action='store_true', help='仅探索用途：关闭统计证据门控')
    p.add_argument('--output', type=Path, default=Path('output'))
    args = p.parse_args()
    source = args.csv.read_bytes()
    demo = args.csv.resolve() == (Path(__file__).parent/'data'/'synthetic_demo.csv').resolve()
    data = load_csv(source, is_demo=demo)
    result = ResearchWorkflow(data).run(count=args.count, model=args.model, test_size=args.test_size,
                                        window=args.window, min_train=args.min_train, seed=args.seed,
                                        use_gate=not args.no_gate)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'candidates.csv').write_text('number\n'+'\n'.join(result.candidate_numbers)+'\n',encoding='utf-8-sig')
    result.backtest.rows.to_csv(args.output/'backtest_details.csv',index=False,encoding='utf-8-sig')
    result.backtest.summary.to_csv(args.output/'backtest_summary.csv',index=False,encoding='utf-8-sig')
    report = {'demo_data':demo,'total_periods':len(data.frame),'count':args.count,'model':args.model,
              'use_gate':not args.no_gate, 'gate':result.gate,'proposals':result.proposals,
              'audit':result.audit,'expected_single_draw_coverage':args.count/100000}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('完成。结果目录：',args.output.resolve())
    print('候选号码数量：',len(result.candidate_numbers))
    print('证据门控：', result.gate)
    print(result.backtest.summary.to_string(index=False))
    if demo:
        print('注意：当前仅为伪随机演示数据，不是真实开奖。')

if __name__=='__main__':
    main()
