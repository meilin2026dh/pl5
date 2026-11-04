"""Local-only PL5 V1.4 algorithm registry management command.

No automatic network/code execution, no HTTP registration or approval endpoint.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import os
import sys
import hashlib

from pailie5.algorithm_registry_v14 import Registry, from_github_rule
from pailie5.integration_bridge import decode_mask


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V1.4 local algorithm admission')
    p.add_argument('--db',default=os.getenv('PL5_REGISTRY_PATH',str(Path('runtime')/'algorithm_registry_v14.sqlite')))
    s=p.add_subparsers(dest='command',required=True)
    i=s.add_parser('import-rule',help='Import an original GitHub rule mask from bridge request JSON')
    i.add_argument('--request',required=True);i.add_argument('--rule-id',required=True)
    i.add_argument('--creator',required=True);i.add_argument('--cutoff-date',required=True)
    i.add_argument('--source-ref',required=True);i.add_argument('--data-sha256',required=True)
    e=s.add_parser('audit',help='Evaluate future-dated CSV/JSON draw array against frozen mask')
    e.add_argument('id');e.add_argument('--draws',required=True)
    a=s.add_parser('approve',help='Research rule approval ONLY; explicit independent reviewer required')
    a.add_argument('id');a.add_argument('--experiment-id',type=int,required=True)
    a.add_argument('--reviewer',required=True);a.add_argument('--consent',required=True)
    v=s.add_parser('revoke');v.add_argument('id');v.add_argument('--reviewer',required=True);v.add_argument('--reason',required=True)
    s.add_parser('list');s.add_parser('verify-ledger')
    x=p.parse_args(argv)
    registry=Registry(x.db)
    try:
        if x.command=='import-rule':
            obj=json.loads(Path(x.request).read_text(encoding='utf-8'))
            if obj.get('combination')!='strict':
                raise ValueError('导入GitHub规则只允许严格AND模式')
            matching=[r for r in obj.get('rules',[]) if r.get('id')==x.rule_id]
            if len(matching)!=1:
                raise ValueError('规则ID在请求中不存在或重复')
            result=from_github_rule(obj,matching[0],creator=x.creator,
                                    cutoff_date=x.cutoff_date,source_ref=x.source_ref,
                                    data_sha256=x.data_sha256,registry=registry)
        elif x.command=='audit':
            raw=Path(x.draws).read_bytes()
            data=json.loads(raw)
            if not isinstance(data,list): raise ValueError('测试文件必须是JSON数组')
            result=registry.evaluate_holdout(x.id,data,snapshot_sha256=hashlib.sha256(raw).hexdigest())
        elif x.command=='approve':
            result=registry.approve_experimental(x.id,experiment_id=x.experiment_id,
                                               reviewer=x.reviewer,consent=x.consent)
        elif x.command=='revoke':
            result=registry.revoke(x.id,reviewer=x.reviewer,reason=x.reason)
        elif x.command=='list': result=registry.list_candidates()
        else: result={'event_chain_verified':registry.verify_ledger()}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        registry.close()


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,PermissionError,FileNotFoundError) as exc:
        print('错误:',str(exc),file=sys.stderr)
        sys.exit(2)
