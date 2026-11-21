"""Extract only a *fresh* native GitHub official-source server cache."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from pailie5.evolution_v15 import canonical, validate_draws

OFFICIAL_URL='https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry'

def extract(cache):
    if not isinstance(cache,dict) or cache.get('sourceUrl')!=OFFICIAL_URL or cache.get('stale') is True:
        raise ValueError('缓存来源不是固定的中国体育彩票接口或已过期标记')
    ts=cache.get('updatedAt')
    if not isinstance(ts,str):raise ValueError('缓存缺少更新时间')
    parsed=datetime.fromisoformat(ts.replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('缓存更新时间缺少时区')
    age=(datetime.now(timezone.utc)-parsed).total_seconds()
    if age < -300 or age > 36*3600:
        raise ValueError('官方缓存超过36小时或时间异常，不能用于自动竞争')
    return validate_draws(cache.get('draws'))

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    x=p.parse_args(argv)
    rows=extract(json.loads(Path(x.cache).read_text(encoding='utf8')))
    dst=Path(x.out);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(canonical(rows)+'\n',encoding='utf8')
    print('缓存已验证结构及时间；并不证明来源具有密码学真实性。记录数：',len(rows))

if __name__=='__main__':main()
