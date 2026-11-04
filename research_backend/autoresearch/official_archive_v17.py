"""PL5 V1.7 official-only incremental history archive.

Never silently correct a published draw, infer missing issues, or regard a copied
URL as a cryptographic attestation of origin. Network fetch is opt-in.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import os
import re
import tempfile

ENDPOINT = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry'
GAME = '350133'
MAX_RESPONSE = 4 * 1024 * 1024


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def checksum(value):
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def _date(value):
    try:
        d = date.fromisoformat(value)
        if d.isoformat() != value or not 1900 <= d.year <= 2100:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('官方开奖日期格式非法') from None
    return value


def validate_rows(rows):
    by_issue, by_date = {}, {}
    if not isinstance(rows, list) or len(rows) > 50000:
        raise ValueError('历史记录数量不合法')
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('开奖记录结构不合法')
        issue, day, number = row.get('issue'), row.get('date'), row.get('number')
        if not isinstance(issue, str) or not re.fullmatch(r'\d{1,20}', issue):
            raise ValueError('期号不合法')
        _date(day)
        if not isinstance(number, str) or not re.fullmatch(r'\d{5}', number):
            raise ValueError('开奖号码不是五位数字')
        if issue in by_issue and by_issue[issue] != row:
            raise ValueError('同一期号开奖冲突：'+issue)
        if day in by_date and by_date[day] != issue:
            raise ValueError('同一日期出现不同期号：'+day)
        by_issue[issue] = {'issue':issue,'date':day,'number':number}
        by_date[day] = issue
    ordered = sorted(by_issue.values(), key=lambda x:(x['date'], int(x['issue'])))
    return ordered


def parse_official(payload):
    if not isinstance(payload, dict) or payload.get('success') is not True:
        raise ValueError('官方接口未返回成功状态')
    value = payload.get('value')
    if not isinstance(value, dict) or not isinstance(value.get('list'), list):
        raise ValueError('官方响应缺少历史列表')
    rows = []
    for item in value['list']:
        if not isinstance(item, dict) or str(item.get('lotteryGameNum')) != GAME:
            raise ValueError('彩种标识不匹配')
        number = re.sub(r'\s+', '', str(item.get('lotteryDrawResult', '')))
        rows.append({'issue':str(item.get('lotteryDrawNum','')),
                     'date':str(item.get('lotteryDrawTime',''))[:10], 'number':number})
    return validate_rows(rows)


def fetch_official_pages(pages=2, *, opener=urlopen):
    if type(pages) is not int or not 1 <= pages <= 20:
        raise ValueError('页数只能为1到20')
    output = []
    for page in range(1,pages+1):
        query = urlencode({'gameNo':GAME,'provinceId':'0','pageSize':'100','isVerify':'1','pageNo':str(page)})
        req = Request(ENDPOINT+'?'+query, headers={'Accept':'application/json', 'User-Agent':'PL5-Research/1.7 (official historical data only)'})
        with opener(req, timeout=20) as response:
            raw = response.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE:raise ValueError('官方返回数据超过4MB上限')
        page_rows = parse_official(json.loads(raw))
        if not page_rows:break
        output.extend(page_rows)
        if len(page_rows) < 100:break
    if not output:raise ValueError('没有获得任何官方开奖记录；不会回退到演示数据')
    return validate_rows(output)


def _atomic(path, content:bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.pl5-', dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(content)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


class OfficialArchive:
    def __init__(self,root):
        self.root = Path(root)
        self.index = self.root/'index.json'
        self.snapshots = self.root/'snapshots'
        self.csv = self.root/'official_history.csv'

    def load(self):
        if not self.index.is_file():return [],None
        manifest=json.loads(self.index.read_text('utf-8'))
        if manifest.get('source') != ENDPOINT:raise ValueError('数据档案来源不匹配')
        version=manifest['version']
        if not re.fullmatch(r'[0-9a-f]{64}',version):raise ValueError('档案版本无效')
        snap=self.snapshots/(version+'.json')
        if not snap.is_file():raise ValueError('档案快照文件丢失')
        rows=json.loads(snap.read_text('utf-8'))
        valid=validate_rows(rows)
        if checksum(valid)!=version or valid!=rows:raise ValueError('官方历史快照完整性校验失败')
        if len(rows)!=manifest['count'] or (rows and rows[-1]['issue']!=manifest['latest_issue']):
            raise ValueError('档案索引与快照不一致')
        return valid,manifest

    def merge(self, incoming, *, checked_at=None):
        updates=validate_rows(incoming)
        if not updates:raise ValueError('不可写入空更新')
        old,manifest=self.load()
        old_by_issue={x['issue']:x for x in old}
        old_by_day={x['date']:x['issue'] for x in old}
        for row in updates:
            i,day=row['issue'],row['date']
            if i in old_by_issue and old_by_issue[i]!=row:
                raise ValueError('官方数据历史期号冲突，阻止静默覆盖：'+i)
            if day in old_by_day and old_by_day[day]!=i:
                raise ValueError('历史日期冲突，阻止静默覆盖：'+day)
        combined=validate_rows(old+updates)
        version=checksum(combined)
        if manifest and version==manifest['version']:
            return {'changed':False,'added':0,'count':len(combined),'latest_issue':combined[-1]['issue'],
                    'version':version,'path':str(self.csv),'source':ENDPOINT}
        checked_at=checked_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
        data=(canonical(combined)+'\n').encode('utf8')
        snapshot=self.snapshots/(version+'.json')
        if snapshot.exists():
            if snapshot.read_bytes()!=data:raise ValueError('快照路径遭到篡改')
        else:
            _atomic(snapshot,data)
        csv='issue,date,number\r\n'+'\r\n'.join(f"{x['issue']},{x['date']},{x['number']}" for x in combined)+'\r\n'
        _atomic(self.csv,csv.encode('utf-8'))
        new_manifest={'schema':'pl5-official-archive-v17','source':ENDPOINT,
                      'checked_at':checked_at,'count':len(combined),'latest_issue':combined[-1]['issue'],
                      'latest_date':combined[-1]['date'],'version':version,
                      'previous_version':manifest['version'] if manifest else None,
                      'origin_cryptographically_verified':False}
        _atomic(self.index,(canonical(new_manifest)+'\n').encode('utf-8'))
        return {'changed':True,'added':len(combined)-len(old),'count':len(combined),
                'latest_issue':combined[-1]['issue'],'version':version,
                'path':str(self.csv),'source':ENDPOINT}

    def sync(self,pages=2,*,fetcher=fetch_official_pages):
        return self.merge(fetcher(pages))

    def status(self):
        rows,manifest=self.load()
        return {'state':'ready' if manifest else 'empty', 'count':len(rows),
                'latest_issue':rows[-1]['issue'] if rows else None,
                'version':manifest['version'] if manifest else None,
                'source':ENDPOINT, 'origin_cryptographically_verified':False}
