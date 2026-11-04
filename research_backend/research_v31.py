"""V3.1 self-extending finite-algebra research CLI (no live betting)."""
import argparse
import json
from pathlib import Path
import numpy as np

from pailie5.primitive_categories_v31 import (
    invent_categories, category_gap_report, CategoryRegistry,
    run_operator_on_100k, compose_abilities, analyze_v29_primitives,
)
from research_v24 import read_history


def run(argv=None):
    parser = argparse.ArgumentParser(description='PL5 V3.1数学类别发现：研究专用，非预测保证')
    parser.add_argument('action', choices=['demo', 'table', 'study'])
    parser.add_argument('--history', type=Path, help='CSV，官方来源由用户独立核实')
    parser.add_argument('--table-json', type=Path, help='100格10×10整数数组JSON')
    parser.add_argument('--maximum', type=int, default=8)
    parser.add_argument('--seed', type=int, default=20261102)
    parser.add_argument('--registry', type=Path, default=Path('runtime/v31_categories.sqlite'))
    parser.add_argument('--report', type=Path, default=Path('reports/v31_categories.json'))
    args = parser.parse_args(argv)
    if args.action == 'study':
        if not args.history: parser.error('study必须指定--history')
        h = read_history(args.history)
        report = analyze_v29_primitives(h, maximum=args.maximum, registry=args.registry)
        report['dataset_source'] = '用户文件；本程序未独立验证官方发布来源'
    else:
        if args.action == 'table':
            if not args.table_json: parser.error('table必须指定--table-json')
            data = json.loads(args.table_json.read_text('utf-8'))
            if not isinstance(data, list): raise ValueError('需要10×10整数数组')
            tables = {'provided': np.asarray(data)}
            source = '用户提供的运算表'
        else:
            a, b = np.indices((10, 10))
            orbit = np.array([0, 2, 1, 0, 1, 2, 2, 1, 0, 2], dtype=np.uint8)
            rng = np.random.default_rng(args.seed)
            random = rng.integers(0, 4, size=(10, 10), dtype=np.uint8)
            random.ravel()[:4] = np.arange(4)
            tables = {'quotient_synthetic': ((a % 2+b % 3) % 3).astype(np.uint8),
                      'cyclic_synthetic': orbit[(a-b)%10],
                      'unstructured_random_control': random}
            source = '合成运算表（不包含彩票开奖数据）'
        db = CategoryRegistry(args.registry)
        items=[]; all_found={}
        for name, table in tables.items():
            found, rejected = invent_categories(table, source_id=name)
            for op in found:
                inserted = db.register(op)
                all_found[op.id] = op
                items.append({'fixture': name, 'ability': op.card(), 'inserted': inserted})
            if not found:
                items.append({'fixture': name, 'gap': category_gap_report(table, source_id=name),
                              'rejections': rejected})
        report = {'version':'v31', 'dataset_source': source,
                  'generated': len(all_found), 'items': items, 'registry': str(args.registry),
                  'scientific_state':'research_only', 'predictive_advantage':'NOT_ESTABLISHED'}
        if args.action == 'demo' and all_found:
            first = next(iter(all_found.values()))
            sample = run_operator_on_100k(first, (0,4), (0,))
            report['esse_experiment'] = {k:v for k,v in sample.items() if k != 'mask'}
            report['aan_composition'] = {k:v for k,v in compose_abilities(
                {'apply': first.id,'args':[{'digit':0},{'digit':4}]}, all_found).items() if k != 'outputs'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f'PL5 V3.1 {args.action}：记录至 {args.report}，新能力 {report.get("generated",0)}，研究专用')
    return report

if __name__ == '__main__': run()
