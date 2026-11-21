"""网络来源适配：公开社区镜像，不冒充中国体彩网官方开奖。

说明：该适配器只允许固定HTTPS主机/路径，不接收任意URL，
没有联网时由用户下载CSV后走离线导入。
"""
from __future__ import annotations
import csv
import io
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit

COMMUNITY_MIRROR_URL='https://raw.githubusercontent.com/BrookeMa/pl5-data/main/pl5_5digit.csv'
MAX_SIZE=8_000_000

class NoHostSwitch(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        if urlsplit(newurl).hostname != 'raw.githubusercontent.com' or urlsplit(newurl).scheme!='https':
            raise ValueError('网络来源发生跨域或非HTTPS重定向，拒绝处理')
        return super().redirect_request(req,fp,code,msg,hdrs,newurl)


def normalize_community_csv(content: bytes) -> bytes:
    """适配 period,date,winningNumber -> period,number，杜绝静默补零。"""
    try:
        reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        if not reader.fieldnames or not {'period','winningNumber'}.issubset(reader.fieldnames):
            raise ValueError('社区镜像格式不符合预期：须含period、winningNumber')
        rows=[]
        for item in reader:
            p=(item['period'] or '').strip(); n=(item['winningNumber'] or '').strip()
            if not p.isdigit() or not re.fullmatch(r'[0-9]{5}',n):
                raise ValueError(f'来源数据包含非法期号或非5位号码（期号：{p}）')
            rows.append((p,n))
        if len(rows)<100:
            raise ValueError('仅获取少量数据，疑似上游截断；拒绝写入')
        if len(set(p for p,_ in rows))!=len(rows):
            raise ValueError('上游包含重复期号，拒绝写入')
        if rows!=sorted(rows,key=lambda x:int(x[0])):
            raise ValueError('来源数据未按期号升序排列，拒绝写入')
        output='period,number\n'+''.join(f'{p},{n}\n' for p,n in rows)
        return output.encode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('来源文件编码错误') from exc


def fetch_community_mirror() -> bytes:
    """显式调用时才联网；严格限制来源与最大内容大小。不能代替官方核验。"""
    req=Request(COMMUNITY_MIRROR_URL,headers={'User-Agent':'Pailie5Research/0.2 (+manual verification)'})
    opener=build_opener(NoHostSwitch())
    with opener.open(req,timeout=25) as response:
        final=response.geturl()
        if final!=COMMUNITY_MIRROR_URL:
            raise ValueError('下载地址与预期不一致')
        content=response.read(MAX_SIZE+1)
    if len(content)>MAX_SIZE:
        raise ValueError('数据源超过最大许可大小，已中止导入')
    return normalize_community_csv(content)
