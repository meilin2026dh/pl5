"""Offline, auditable PL5 V1.5 competition + safe DSL proposal command-line.

V1.0 ongoing online discovery is run independently by the existing research_v10
scheduler. This CLI has no background process, keys or purchase actions.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from pailie5.integration_bridge import decode_mask
from pailie5.algorithm_registry_v14 import Registry
from pailie5.evolution_v15 import EvolutionLab, Policy, canonical, digest, validate_draws


def read_json(path):
    raw=Path(path).read_bytes()
    if len(raw)>5*1024*1024:
        raise ValueError('输入文件不得大于5MB')
    return json.loads(raw)


def main(argv=None):
    parser=argparse.ArgumentParser(description='PL5 V1.5 竞争评估和安全算法生长（无自动批准）')
    parser.add_argument('--db',default='runtime/algorithm_registry_v14.sqlite')
    commands=parser.add_subparsers(dest='cmd',required=True)
    p=commands.add_parser('scan',help='分析冻结规则的历史后验表现与边际压缩')
    p.add_argument('--draws',required=True);p.add_argument('--source-label',required=True)
    p.add_argument('--reference-issue');p.add_argument('--base-mask-json')
    p.add_argument('--auto-pause',action='store_true',help='仅在强漏删异常时自动暂停已经批准的实验规则')
    p.add_argument('--report')
    a=commands.add_parser('propose',help='基于受限DSL研究文本自动生成待审核规则')
    a.add_argument('--text',required=True);a.add_argument('--history',required=True)
    a.add_argument('--source-key',required=True);a.add_argument('--source-ref',required=True)
    a.add_argument('--creator',default='v15-research-agent');a.add_argument('--base-mask-json')
    a.add_argument('--max-proposals',type=int,default=4);a.add_argument('--report')
    r=commands.add_parser('resume',help='人工复审后解除V1.5健康暂停')
    r.add_argument('algorithm_id');r.add_argument('--reviewer',required=True);r.add_argument('--reason',required=True)
    commands.add_parser('status');commands.add_parser('verify-ledger')
    opts=parser.parse_args(argv)
    with_registry=Registry(opts.db)
    try:
        lab=EvolutionLab(with_registry)
        if opts.cmd=='scan':
            base=decode_mask(read_json(opts.base_mask_json)) if opts.base_mask_json else None
            report=lab.scan(read_json(opts.draws),source_label=opts.source_label,
                            reference_issue=opts.reference_issue,source_mask=base,
                            auto_pause=opts.auto_pause)
        elif opts.cmd=='propose':
            base=decode_mask(read_json(opts.base_mask_json)) if opts.base_mask_json else None
            rows=read_json(opts.history)
            # Data snapshot is supplied and hashed here; do not trust an unbound manual checksum.
            report=lab.propose_from_text(text=Path(opts.text).read_text(encoding='utf-8'),
                source_key=opts.source_key,history=rows,data_sha256=digest(validate_draws(rows)),
                creator=opts.creator,source_ref=opts.source_ref,source_mask=base,
                policy=Policy(max_auto_proposals=opts.max_proposals))
        elif opts.cmd=='resume':
            report={'resumed':lab.resume(opts.algorithm_id,reviewer=opts.reviewer,
                                         explanation=opts.reason),'id':opts.algorithm_id}
        elif opts.cmd=='status':
            cs=with_registry.list_candidates()
            report={'candidates':len(cs),'approved':sum(x['state']=='approved_experimental' for x in cs),
                    'suspended':[x['id'] for x in cs if lab.paused(x['id'])],
                    'scans':with_registry.db.execute('SELECT COUNT(*) FROM v15_scans').fetchone()[0],
                    'proposals':with_registry.db.execute('SELECT COUNT(*) FROM v15_proposals').fetchone()[0]}
        else:report={'event_chain_verified':with_registry.verify_ledger()}
        if getattr(opts,'report',None):
            destination=Path(opts.report);destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(canonical(report)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    finally:with_registry.close()

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,PermissionError,FileNotFoundError) as exc:
        print('V1.5错误:',str(exc),file=sys.stderr);sys.exit(2)
