"""Official APIs for publications and repositories; no code execution or web scraping.

Documents are UNTRUSTED DATA. Only metadata and abstracts enter the research queue.
Network access is explicit; tests use a replacement fetcher. Never follow user supplied URLs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET
import json
import os
import re
import time

UA = 'PL5-AutoResearch/0.5 (research metadata only; follow API policies)'
MAX_BYTES = 2_000_000

@dataclass(frozen=True)
class Paper:
    key: str
    source: str
    title: str
    abstract: str
    url: str
    date: str
    topic: str
    authors: str = ''

    def to_dict(self): return asdict(self)


def _json_get(url: str) -> dict:
    """Endpoint is built only from static provider domains; bounded download and timeout."""
    if not url.startswith(('https://api.openalex.org/works?',
                           'https://api.github.com/search/repositories?')):
        raise ValueError('未授权的研究来源URL')
    headers = {'User-Agent': UA, 'Accept': 'application/json'}
    token = os.getenv('GITHUB_TOKEN') if 'api.github.com' in url else None
    if token:
        headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request(url,headers=headers),timeout=16) as response:
        content = response.read(MAX_BYTES + 1)
        if len(content)>MAX_BYTES:
            raise ValueError('研究来源响应超过2MB安全限制')
        return json.loads(content)


def _xml_get(url: str) -> bytes:
    if not url.startswith('https://export.arxiv.org/api/query?'):
        raise ValueError('未授权的arXiv URL')
    with urlopen(Request(url,headers={'User-Agent': UA}),timeout=16) as response:
        content = response.read(MAX_BYTES + 1)
        if len(content)>MAX_BYTES:
            raise ValueError('arXiv响应超过2MB安全限制')
        return content


def _reconstruct_abstract(idx: dict | None) -> str:
    if not isinstance(idx,dict): return ''
    positions = [(int(i),str(word)) for word, offsets in idx.items() for i in offsets if isinstance(i,int)]
    positions.sort()
    return ' '.join(word for _,word in positions)[:4000]


def collect_openalex(topic: str, since: str, limit: int = 8, *, get=_json_get) -> list[Paper]:
    params = {'search': topic, 'filter': f'from_publication_date:{since}',
              'per_page': max(1,min(int(limit),25)), 'sort': 'publication_date:desc'}
    if os.getenv('OPENALEX_API_KEY'): params['api_key'] = os.environ['OPENALEX_API_KEY']
    data = get('https://api.openalex.org/works?' + urlencode(params))
    result = []
    for item in data.get('results',[]):
        key = item.get('doi') or item.get('id')
        url = item.get('doi') or item.get('id')
        if not key or not url: continue
        authors = ', '.join(x.get('author',{}).get('display_name','') for x in item.get('authorships',[])[:5])
        result.append(Paper(str(key), 'openalex', str(item.get('display_name') or ''),
                            _reconstruct_abstract(item.get('abstract_inverted_index')),
                            str(url), str(item.get('publication_date') or ''),topic,authors))
    return result


def collect_arxiv(topic: str, limit: int = 8, *, get=_xml_get) -> list[Paper]:
    # arXiv API syntax. Search by individual quoted terms; no arbitrary query string injection.
    safe = re.sub('[^A-Za-z0-9 -]',' ',topic).strip()[:70]
    params = {'search_query': 'all:"'+safe+'"', 'start':0,
              'max_results':max(1,min(int(limit),25)), 'sortBy':'submittedDate', 'sortOrder':'descending'}
    root = ET.fromstring(get('https://export.arxiv.org/api/query?' + urlencode(params)))
    ns = {'a':'http://www.w3.org/2005/Atom'}
    out=[]
    for e in root.findall('a:entry',ns):
        uid = (e.findtext('a:id','',ns) or '').strip()
        title = ' '.join((e.findtext('a:title','',ns) or '').split())
        abstract = ' '.join((e.findtext('a:summary','',ns) or '').split())[:4000]
        published = (e.findtext('a:published','',ns) or '')[:10]
        authors = ', '.join(x.findtext('a:name','',ns) for x in e.findall('a:author',ns))
        if uid and title: out.append(Paper(uid,'arxiv',title,abstract,uid,published,topic,authors))
    return out


def collect_github(topic: str, since: str, limit: int = 8, *, get=_json_get) -> list[Paper]:
    # github results are discovery leads, not executable dependencies.
    query = f'{topic} pushed:>={since} archived:false'
    params = {'q':query, 'sort':'updated','order':'desc', 'per_page':max(1,min(int(limit),20))}
    data = get('https://api.github.com/search/repositories?' + urlencode(params))
    return [Paper('github:'+str(x['id']),'github',str(x.get('full_name') or ''),
                  str(x.get('description') or '')[:4000],str(x.get('html_url') or ''),
                  str(x.get('pushed_at') or '')[:10],topic,str((x.get('license') or {}).get('spdx_id') or ''))
            for x in data.get('items',[]) if x.get('id') is not None]


DEFAULT_TOPICS = [
    'sequential multiple testing', 'online conformal prediction',
    'distribution shift detection', 'minimum description length',
    'randomness testing', 'combinatorial ranking',
    'probabilistic graphical models', 'automated scientific discovery',
]


def collect_all(topics: list[str] | None = None, *, days: int=21, limit: int=6,
                providers: tuple[str,...]=('openalex','arxiv','github')) -> tuple[list[Paper],list[dict]]:
    """Return (metadata, failures); a failing provider must not abort a successful scan."""
    since = (date.today()-timedelta(days=days)).isoformat()
    papers=[]; errors=[]
    for topic in (topics or DEFAULT_TOPICS):
        for provider in providers:
            fn = {'openalex':lambda:collect_openalex(topic,since,limit),
                  'arxiv':lambda:collect_arxiv(topic,limit),
                  'github':lambda:collect_github(topic,since,limit)}.get(provider)
            if fn is None: raise ValueError(f'未知来源 {provider}')
            try: papers.extend(fn())
            except (HTTPError,URLError,TimeoutError,ValueError,ET.ParseError,KeyError,OSError) as exc:
                errors.append({'provider':provider,'topic':topic,'error':str(exc)[:350]})
            # Low request rate, be respectful to the providers.
            if provider == 'arxiv': time.sleep(3.0)  # Follow arXiv API's documented courteous 3s spacing
    return papers,errors
