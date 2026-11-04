"""Deterministic PL5 ranked candidate artifacts tied to an exact CSV and source code.

Local commitment is NOT evidence of pre-draw timing. Export the digest to an
independent trusted timestamp/append-only public log BEFORE draw and preserve its
receipt separately. Only hashes and inputs can be locally recomputed here.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import sys
import numpy as np

from .lab import Hypothesis, rank_100
from .integrated_v10 import canon, sha
from pailie5.data import load_csv

KERNEL_FILES=('autoresearch/lab.py','pailie5/pattern_rules.py',
              'pailie5/space_mapping.py','pailie5/engine.py')


def kernels(root:Path):
    return {p:sha256((root/p).read_bytes()).hexdigest() for p in KERNEL_FILES}


def history(csv_path:Path,source:str):
    if not str(source).startswith(('official:','https://')):
        raise ValueError('必须提供人工核验的官方数据来源说明（official:...或官方HTTPS链接）')
    raw=csv_path.read_bytes()
    draws=load_csv(raw)
    if draws.warnings:
        # Even automatically sorted or nonnumeric period order must be explicitly corrected.
        raise ValueError('开奖数据存在警告，须先核验修正：'+'；'.join(draws.warnings))
    if not draws.frame['period'].str.fullmatch(r'[0-9]{4,16}').all():
        raise ValueError('期号必须为4-16位数字')
    return {'numbers':draws.frame['number'].tolist(),
            'previous_period':str(draws.frame['period'].iloc[-1]),
            'history_sha256':sha256(raw).hexdigest(), 'rows':len(draws.frame)}


class CandidateBundles:
    def __init__(self,db:sqlite3.Connection,root:Path):
        self.db=db
        self.root=Path(root)
        self.db.row_factory=sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v10_bundles(
          model_id TEXT NOT NULL,target_period TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,
          history_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,artifact_path TEXT NOT NULL,
          PRIMARY KEY(model_id,target_period));
        CREATE TRIGGER IF NOT EXISTS v10_bundles_no_update BEFORE UPDATE ON v10_bundles
          BEGIN SELECT RAISE(ABORT,'immutable_candidate_manifest');END;
        CREATE TRIGGER IF NOT EXISTS v10_bundles_no_delete BEFORE DELETE ON v10_bundles
          BEGIN SELECT RAISE(ABORT,'immutable_candidate_manifest');END;
        ''')
        db.commit()

    def issue(self,*,csv_path,official_source,target_period,k=100,model_name='shadow-rules',salt='pl5-v10',output_dir='research_reports/v10_commits',allow_empty_baseline=False):
        if not re.fullmatch(r'[0-9]{4,16}',str(target_period)):
            raise ValueError('待预测期号格式错误')
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,100}',model_name):
            raise ValueError('模型名称必须安全且非空')
        if not 1<=k<=100:raise ValueError('最多允许100注')
        d=history(Path(csv_path),official_source)
        if int(target_period)<=int(d['previous_period']):
            raise ValueError('目标期号不得早于或等于历史最后一期')
        rows=self.db.execute("SELECT specification FROM hypotheses WHERE status='shadow' ORDER BY fingerprint LIMIT 24").fetchall()
        specs=[Hypothesis(**json.loads(r['specification'])) for r in rows]
        if not specs and not allow_empty_baseline:
            raise ValueError('当前未设定shadow研究规则；如要纯随机基线请显式 --allow-empty-baseline')
        fp=sha([s.as_dict() for s in specs])
        sources=kernels(self.root)
        model={'model_name':model_name,'specifications':[s.as_dict() for s in specs],
               'salt':salt,'kernel_sha256':sources,'model_spec_sha256':fp,'ranking_policy':'rank_100:v10',
               'numpy_version':np.__version__,'python_minor':f'{sys.version_info.major}.{sys.version_info.minor}'}
        mid=sha(model)
        if self.db.execute('SELECT 1 FROM v10_bundles WHERE model_id=? AND target_period=?',(mid,str(target_period))).fetchone():
            raise ValueError('该模型该期已经封存，不能覆盖或重新生成')
        candidates,evidence=rank_100(d['numbers'],specs,k=k,salt=salt)
        manifest={'schema':'pl5-commit-v10','model_id':mid,'model':model,
                  'source_declaration':official_source,'previous_period':d['previous_period'],
                  'target_period':str(target_period),'history_sha256':d['history_sha256'],
                  'history_rows':d['rows'],'candidates':candidates,'evidence':evidence,
                  'created_at_local':datetime.now(timezone.utc).isoformat(),
                  'external_timestamp_verified':False,
                  'research_only':True, 'predictive_advantage_proven':False}
        manifest['manifest_sha256']=sha(manifest)
        output_dir=Path(output_dir)
        output_dir.mkdir(parents=True,exist_ok=True)
        path=output_dir/f'{str(target_period)}_{mid[:12]}.json'
        # Atomic new-file semantics: never overwrite a prior sealed manifest.
        try:
            with path.open('x',encoding='utf-8') as f:
                json.dump(manifest,f,ensure_ascii=False,indent=2)
        except FileExistsError:
            raise ValueError('存在同名封存文件，拒绝覆盖') from None
        try:
            self.db.execute('INSERT INTO v10_bundles VALUES(?,?,?,?,?,?)',
                (mid,str(target_period),manifest['manifest_sha256'],d['history_sha256'],
                 manifest['created_at_local'],str(path)))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {'model_id':mid,'manifest_sha256':manifest['manifest_sha256'],
                'artifact_path':str(path),'candidate_count':len(candidates),
                'local_only':True,'trusted_pre_draw_proof':False}

    def verify(self,artifact_path,csv_path,*,require_model_in_ledger=False):
        payload=json.loads(Path(artifact_path).read_text(encoding='utf-8'))
        expected=payload.get('manifest_sha256')
        content={k:v for k,v in payload.items() if k!='manifest_sha256'}
        intact=expected==sha(content)
        model=payload['model']
        same_model=payload['model_id']==sha(model)
        same_code=(model['kernel_sha256']==kernels(self.root) and
                   model.get('numpy_version')==np.__version__ and
                   model.get('python_minor')==f'{sys.version_info.major}.{sys.version_info.minor}')
        d=history(Path(csv_path),payload['source_declaration'])
        same_history=d['history_sha256']==payload['history_sha256'] and d['rows']==payload['history_rows'] and d['previous_period']==payload['previous_period']
        cands=payload['candidates']
        if not 1<=len(cands)<=100 or len(set(cands))!=len(cands) or any(not isinstance(x,str) or not re.fullmatch(r'[0-9]{5}',x) for x in cands):
            raise ValueError('候选集不合法')
        specs=[Hypothesis(**x) for x in model['specifications']]
        reranked,ev=rank_100(d['numbers'],specs,k=len(cands),salt=model['salt'])
        same_ranking=reranked==cands and ev==payload['evidence']
        row=self.db.execute('SELECT * FROM v10_bundles WHERE model_id=? AND target_period=?',
                            (payload['model_id'],payload['target_period'])).fetchone()
        same_ledger=bool(row and row['manifest_sha256']==expected and row['history_sha256']==payload['history_sha256'])
        ok=all((intact,same_model,same_code,same_history,same_ranking)) and (same_ledger or not require_model_in_ledger)
        return {'verified_locally':bool(ok),'manifest_integrity':intact,'model_identity':same_model,
                'current_source_matches':same_code,'history_bytes_match':same_history,
                'candidates_recomputed_equal':same_ranking,'sqlite_record_matches':same_ledger,
                'external_timestamp_verified':False,
                'limitation':'本地哈希不是第三方开奖前时间证明，且数据官方来源仅为人工声明'}
