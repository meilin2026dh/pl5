"""Limited local PDF or verified arXiv PDF full-text intake; never arbitrary URLs.

No OCR, JavaScript, external code, redirects to arbitrary hosts or repository installs.
Untrusted document content is treated as evidence only, not executable instructions.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen,Request,build_opener,HTTPRedirectHandler
import re

MAX_PDF=8_000_000
MAX_TEXT=70_000


def extract_pdf_bytes(content:bytes):
    if len(content)>MAX_PDF or not content.startswith(b'%PDF-'):
        raise ValueError('必须是8MB以内的真实PDF')
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError('请安装可选依赖 pymupdf 后再读取PDF全文') from e
    doc=fitz.open(stream=content,filetype='pdf')
    if doc.needs_pass:raise ValueError('不允许加密PDF')
    try:
        parts=[];length=0
        for i in range(min(24,len(doc))):
            extracted=doc[i].get_text(sort=True)
            if extracted:
                parts.append(extracted);length+=len(extracted)
            if length>=MAX_TEXT:break
        text='\n'.join(parts)[:MAX_TEXT]
        if len(text.strip())<100:raise ValueError('PDF没有足够可提取的正文文本')
        return text
    finally:doc.close()


def read_local_document(file_path):
    path=Path(file_path)
    if path.stat().st_size>MAX_PDF:raise ValueError('文献超过大小限制')
    blob=path.read_bytes()
    if path.suffix.lower()=='.pdf':text=extract_pdf_bytes(blob)
    elif path.suffix.lower() in ('.txt','.md'):
        if len(blob)>MAX_TEXT*4:raise ValueError('文本太大')
        text=blob.decode('utf-8-sig')[:MAX_TEXT]
    else:raise ValueError('仅支持PDF/TXT/MD文献')
    if len(text.strip())<30:raise ValueError('文献内容不足')
    return text,sha256(blob).hexdigest()


def arxiv_id_from_metadata(key:str):
    # Accept only modern numeric IDs, optionally version; do not accept arbitrary paths.
    m=re.fullmatch(r'(?:https://(?:www\.)?arxiv\.org/abs/)?(\d{4}\.\d{4,5})(?:v\d{1,3})?',key)
    if not m:raise ValueError('仅支持格式正确的arXiv新式论文编号')
    return m.group(1)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('PDF下载重定向被禁用；请手动下载后使用本地导入')


def fetch_arxiv_pdf(key:str,*,get_bytes=None):
    ident=arxiv_id_from_metadata(key)
    url=f'https://arxiv.org/pdf/{ident}'
    if get_bytes is None:
        opener=build_opener(_NoRedirect)
        def get_bytes(url):
            with opener.open(Request(url,headers={'User-Agent':'PL5-AutoResearch/0.6 (academic research)'}),timeout=20) as response:
                size=int(response.headers.get('Content-Length','0'))
                if size>MAX_PDF:raise ValueError('PDF大小超过限制')
                return response.read(MAX_PDF+1)
    blob=get_bytes(url)
    return extract_pdf_bytes(blob),sha256(blob).hexdigest(),url
