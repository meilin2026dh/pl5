"""Paper-to-experiment provenance: a cautious *adaptation* protocol.

No fake claim that a generated formula faithfully reproduces an arbitrary paper.
"""
from __future__ import annotations
from hashlib import sha256
from .formulas import invent_from_text


def build_research_protocol(document:dict,limit=3):
    if not 1<=limit<=10:raise ValueError('文献假设数量须在1..10')
    key=document['doc_key'];txt=document['text_excerpt'];kind=document['kind']
    if kind not in ('local','arxiv_pdf','abstract'):raise ValueError('不支持的论文来源')
    if len(txt)<30:raise ValueError('研究材料太短')
    hypotheses=invent_from_text(txt,key,limit=limit)
    return {
        'document_id':key,'document_title':document['title'],'kind':kind,
        'text_sha256':sha256(txt.encode()).hexdigest(),
        'document_source_url':document.get('source_url',''),
        'full_text_read':kind in ('local','arxiv_pdf'),
        'paper_method_reproduced':False,
        'study_type':'bounded_formula_adaptation_not_faithful_paper_replication',
        'hypotheses':[{'fingerprint':x.fingerprint(),'proposed_formula':x.formula,
                       'pattern':x.pattern,'window':x.window,
                       'claim':'待检验的迁移假设；不是论文作者提出的排列五预测公式'} for x in hypotheses],
        'independent_implementation_plan':[
            '使用原始论文的公式/伪代码列出逐项实现对照表（须人工核对）',
            '用独立NumPy与纯Python解释器验证受限指标公式一致性',
            '使用公平独立模拟数据和事先锁定的逐期样本外验证',
            '结果与等规模随机号码集合比较，登记所有失败试验'
        ],
        'uncertainties':(['仅获得摘要，没有论文全文'] if kind=='abstract' else [])+[
            '未人工核验论文方法和数学假设，不得声称完整复现',
            '即使复现成功也不能证明号码预测能力'
        ],
    }
