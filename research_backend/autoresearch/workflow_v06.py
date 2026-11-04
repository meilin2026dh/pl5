"""Auditable autonomous pipeline: intake -> invent -> reproduce -> falsify -> registry.
The steps run synchronously locally or via external scheduler; no background claims.
"""
from __future__ import annotations
from hashlib import sha256
from .formulas import invent_from_text,emit_review_code
from .verification import full_audit


def run_for_document(registry,document_key,draws=None,*,data_sha256=None,
                     limit=4,eval_size=80,null_sequences=4,k=100):
    doc=registry.get_document(document_key)
    invented=invent_from_text(doc['text_excerpt'],document_key,limit=limit)
    output={'document_key':document_key,'source_kind':doc['kind'],
            'new_algorithms':0,'experiments':[],'manual_gate_required':True}
    for algo in invented:
        info=registry.add_algorithm(algo,document_key)
        output['new_algorithms']+=int(info['new'])
        entry={'fingerprint':algo.fingerprint(),'status':'invented','formula':algo.formula,
               'review_code':emit_review_code(algo.formula)}
        existing=registry.has_audit(algo.fingerprint(),data_sha256) if draws is not None else None
        if existing:
            entry.update({'status':'already_tested_on_this_dataset','audit_id':existing,
                          'warning':'同数据指纹已做实验，定时任务不会重复开封'})
        elif draws is not None:
            audit=full_audit(algo,draws,k=k,eval_size=eval_size,
                             null_sequences=null_sequences,attempts=registry.audit_attempts())
            rec=registry.add_audit(algo.fingerprint(),data_sha256,audit)
            entry.update({'status':'audited_not_approved','audit_id':rec['audit_id'],
                          'audit_sha256':rec['sha256'],'engineering_ok':audit['engineering_reproduced'],
                          'hits':audit['development']['hits'],'n':audit['development']['n'],
                          'adjusted_exploratory_p':audit['bonferroni_exploratory_p'],
                          'null_hits':audit['development']['null_hits']})
        output['experiments'].append(entry)
    return output
