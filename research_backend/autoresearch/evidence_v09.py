"""V0.9 prospective, family-wise error-controlled research evidence ledger.

Under the mathematical null of conditionally uniform independent draws, each
predeclared K-set's hit has conditional probability K/100000. Fixed mixtures
of Bernoulli likelihood ratios are nonnegative martingales; Ville's inequality
controls anytime crossings. Each newly registered model receives immutable
alpha_i = alpha/(i(i+1)) (sum <= alpha), and the union bound controls the
probability of *any* false crossing, regardless of cross-model dependence.

VALIDITY CONDITIONS: Real predictions must be irrevocably committed BEFORE
an unknown official result, with no missing adverse outcomes, and outcome
records must be complete. This local SQLite system cannot independently prove
clock chronology, true official sourcing, or tamper resistance against admin.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import math
import re
import sqlite3
from typing import Any

N=100_000
FACTORS=(1.5,2.0,5.0,10.0)
ALPHA=0.05
HEX64=re.compile(r'^[a-f0-9]{64}$')
PERIOD=re.compile(r'^[0-9]{4,16}$')
NUMBER=re.compile(r'^[0-9]{5}$')


def canon(obj:Any)->str:
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(obj:Any)->str:
    return sha256(canon(obj).encode('utf-8')).hexdigest()


def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')


def require_sha(s:str):
    if not isinstance(s,str) or not HEX64.fullmatch(s):raise ValueError('SHA256格式错误')


def require_period(s:str):
    if not isinstance(s,str) or not PERIOD.fullmatch(s):raise ValueError('期号必须为4..16位数字')


def _valid_candidates(candidates):
    if not isinstance(candidates,list) or not 1<=len(candidates)<=100 or len(set(candidates))!=len(candidates):
        raise ValueError('每期必须提交1至100个不重复的候选号码')
    if any(not isinstance(s,str) or not NUMBER.fullmatch(s) for s in candidates):
        raise ValueError('候选号码必须保留五位字符串格式')


def log_e_value(rows:list[dict])->dict:
    """A fixed mixture of 4 e-processes, never adaptively tune factors using results."""
    lr=[0.0 for _ in FACTORS]
    for row in rows:
        p=row['k']/N
        hit=int(row['hit'])
        if not 0<p<=0.001 or hit not in (0,1):raise ValueError('无效期次统计记录')
        for index,multiplier in enumerate(FACTORS):
            q=min(0.5,p*multiplier)
            lr[index]+= math.log(q/p) if hit else math.log1p(-q)-math.log1p(-p)
    shifted=[x-math.log(len(FACTORS)) for x in lr]
    biggest=max(shifted)
    logvalue=biggest+math.log(sum(math.exp(x-biggest) for x in shifted))
    return {'log_e':logvalue,'e_value':math.exp(logvalue) if logvalue<690 else None,
            'fixed_multipliers':list(FACTORS)}


class EvidenceLedger:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v09_models(
          seq INTEGER PRIMARY KEY AUTOINCREMENT,model_id TEXT UNIQUE NOT NULL,
          code_sha256 TEXT NOT NULL,protocol_id TEXT NOT NULL,registered_at TEXT NOT NULL,
          alpha_weight REAL NOT NULL,alpha_allocated REAL NOT NULL,
          registration_json TEXT NOT NULL,registration_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v09_commits(
          model_id TEXT NOT NULL,target_period TEXT NOT NULL,previous_period TEXT NOT NULL,
          candidates_json TEXT NOT NULL,created_at TEXT NOT NULL,
          history_sha256 TEXT NOT NULL,source_description TEXT NOT NULL,
          record_sha256 TEXT NOT NULL,PRIMARY KEY(model_id,target_period));
        CREATE TABLE IF NOT EXISTS v09_official_outcomes(
          target_period TEXT PRIMARY KEY,number TEXT NOT NULL,
          source_description TEXT NOT NULL,data_sha256 TEXT NOT NULL,
          observed_at TEXT NOT NULL,record_sha256 TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS v09_models_immutable_update BEFORE UPDATE ON v09_models
        BEGIN SELECT RAISE(ABORT,'immutable_v09_model');END;
        CREATE TRIGGER IF NOT EXISTS v09_models_immutable_delete BEFORE DELETE ON v09_models
        BEGIN SELECT RAISE(ABORT,'immutable_v09_model');END;
        CREATE TRIGGER IF NOT EXISTS v09_commits_immutable_update BEFORE UPDATE ON v09_commits
        BEGIN SELECT RAISE(ABORT,'immutable_v09_commit');END;
        CREATE TRIGGER IF NOT EXISTS v09_commits_immutable_delete BEFORE DELETE ON v09_commits
        BEGIN SELECT RAISE(ABORT,'immutable_v09_commit');END;
        CREATE TRIGGER IF NOT EXISTS v09_outcomes_immutable_update BEFORE UPDATE ON v09_official_outcomes
        BEGIN SELECT RAISE(ABORT,'immutable_v09_outcome');END;
        CREATE TRIGGER IF NOT EXISTS v09_outcomes_immutable_delete BEFORE DELETE ON v09_official_outcomes
        BEGIN SELECT RAISE(ABORT,'immutable_v09_outcome');END;
        ''')
        db.commit()

    def register_model(self,*,model_id:str,code_sha256:str,protocol_id:str,reviewer:str)->dict:
        if not isinstance(model_id,str) or not re.fullmatch(r'[a-zA-Z0-9_.\-]{3,100}',model_id):
            raise ValueError('模型ID限3..100字符、字母数字下划线点横线')
        require_sha(code_sha256);require_sha(protocol_id)
        if not reviewer or len(reviewer)>120:raise ValueError('必须有审查人姓名/代号')
        if not self.db.execute('SELECT 1 FROM v08_python_candidates WHERE id=?',(code_sha256,)).fetchone():
            raise ValueError('模型必须对应V0.8已有代码指纹')
        row=self.db.execute('SELECT code_id FROM v09_protocols WHERE protocol_id=?',(protocol_id,)).fetchone()
        if not row or row['code_id']!=code_sha256:raise ValueError('模型与已登记的研究协议不匹配')
        # Sequenced allocation. SQLite serialized writer prevents two registrations with same rank.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            seq=int(self.db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM v09_models').fetchone()[0])
            weight=1/(seq*(seq+1))
            t=utc()
            registration={'seq':seq,'model_id':model_id,'code_sha256':code_sha256,
                          'protocol_id':protocol_id,'registered_at':t,'alpha_weight':weight,
                          'alpha_allocated':ALPHA*weight,'reviewer':reviewer,
                          'warning':'local preregistration is not independently timestamped'}
            record_sha=digest(registration)
            self.db.execute('''INSERT INTO v09_models(seq,model_id,code_sha256,protocol_id,
                 registered_at,alpha_weight,alpha_allocated,registration_json,registration_sha256)
                 VALUES(?,?,?,?,?,?,?,?,?)''',(seq,model_id,code_sha256,protocol_id,t,
                   weight,ALPHA*weight,canon(registration),record_sha))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {**registration,'registration_sha256':record_sha,
                'conclusion':'统计检验系列已注册，但不代表模型预测有效'}

    def seal(self,*,model_id:str,target_period:str,previous_period:str,
             candidates:list[str],history_sha256:str,source_description:str)->dict:
        require_period(target_period);require_period(previous_period);require_sha(history_sha256)
        _valid_candidates(candidates)
        if int(target_period)<=int(previous_period):raise ValueError('目标期号必须晚于当前历史期号')
        if not source_description.strip():raise ValueError('开奖数据官方来源声明不能为空')
        row=self.db.execute('SELECT * FROM v09_models WHERE model_id=?',(model_id,)).fetchone()
        if not row:raise ValueError('模型未先行注册')
        # Check outcomes across all models: no late commits after observed result.
        latest=self.db.execute('SELECT MAX(CAST(target_period AS INTEGER)) FROM v09_official_outcomes').fetchone()[0]
        if latest is not None and int(target_period)<=int(latest):
            raise ValueError('该期或后续期开奖结果已入库，禁止事后补交')
        most_recent=self.db.execute('SELECT MAX(CAST(target_period AS INTEGER)) FROM v09_commits WHERE model_id=?',(model_id,)).fetchone()[0]
        if most_recent is not None and int(target_period)<=int(most_recent):
            raise ValueError('每个模型封存期号必须严格递增')
        timestamp=utc()
        content={'model_id':model_id,'target_period':target_period,'previous_period':previous_period,
                 'candidates':sorted(candidates),'created_at':timestamp,'history_sha256':history_sha256,
                 'source_description':source_description,'registration_sha256':row['registration_sha256']}
        sha=digest(content)
        self.db.execute('''INSERT INTO v09_commits(model_id,target_period,previous_period,candidates_json,
             created_at,history_sha256,source_description,record_sha256) VALUES(?,?,?,?,?,?,?,?)''',
             (model_id,target_period,previous_period,canon(sorted(candidates)),timestamp,
              history_sha256,source_description,sha))
        self.db.commit()
        return {'model_id':model_id,'period':target_period,'k':len(candidates),
                'commit_sha256':sha,'local_timestamp':timestamp,
                'warning':'必须在真正开奖前封存，建议将哈希及时提交至不可篡改第三方时间戳服务'}

    def settle(self,*,target_period:str,number:str,source_description:str,data_sha256:str)->dict:
        require_period(target_period);require_sha(data_sha256)
        if not isinstance(number,str) or not NUMBER.fullmatch(number):raise ValueError('开奖号必须是5位数字字符串')
        if not source_description.strip():raise ValueError('官方来源核验声明不能为空')
        row=self.db.execute('SELECT COUNT(*) FROM v09_commits WHERE target_period=?',(target_period,)).fetchone()
        if not row[0]:raise ValueError('没有任何已预登记的该期实验')
        observed=utc()
        content={'target_period':target_period,'number':number,'source_description':source_description,
                 'data_sha256':data_sha256,'observed_at':observed}
        sig=digest(content)
        self.db.execute('''INSERT INTO v09_official_outcomes VALUES(?,?,?,?,?,?)''',
                        (target_period,number,source_description,data_sha256,observed,sig))
        self.db.commit()
        return {'period':target_period,'record_sha256':sig,'settled':True,
                'warning':'仅登记所声明的官方数据来源，代码没有自行核验官方公告'}

    def model_report(self,model_id:str)->dict:
        model=self.db.execute('SELECT * FROM v09_models WHERE model_id=?',(model_id,)).fetchone()
        if not model:raise ValueError('模型未注册')
        register=json.loads(model['registration_json'])
        valid=digest(register)==model['registration_sha256']
        rows=self.db.execute('''SELECT c.*,o.number,o.source_description AS actual_source,
              o.data_sha256 AS actual_data_sha256,o.observed_at,o.record_sha256 AS actual_sha
              FROM v09_commits c LEFT JOIN v09_official_outcomes o USING(target_period)
              WHERE c.model_id=? ORDER BY CAST(c.target_period AS INTEGER)''',(model_id,)).fetchall()
        prefix=[];pending=False;missing=0;bad_hashes=[]
        for row in rows:
            cands=json.loads(row['candidates_json'])
            content={'model_id':model_id,'target_period':row['target_period'],
              'previous_period':row['previous_period'],'candidates':cands,
              'created_at':row['created_at'],'history_sha256':row['history_sha256'],
              'source_description':row['source_description'],
              'registration_sha256':model['registration_sha256']}
            if digest(content)!=row['record_sha256']:
                valid=False;bad_hashes.append(row['target_period'])
            if row['number'] is not None:
                official_content={'target_period':row['target_period'],'number':row['number'],
                  'source_description':row['actual_source'],'data_sha256':row['actual_data_sha256'],
                  'observed_at':row['observed_at']}
                if digest(official_content)!=row['actual_sha']:
                    valid=False;bad_hashes.append('outcome:'+row['target_period'])
            if row['number'] is None:
                pending=True;missing+=1
            elif not pending:
                prefix.append({'period':row['target_period'],'k':len(cands),
                               'hit':int(row['number'] in cands)})
        e=log_e_value(prefix)
        threshold=math.log(1/model['alpha_allocated'])
        # A missing earlier settlement suspends declaration (cannot cherry-pick).
        crosses=bool(valid and not pending and e['log_e']>=threshold)
        return {'model_id':model_id,'series_index':model['seq'],'alpha_family':ALPHA,
                'alpha_allocated':model['alpha_allocated'],
                'anytime_log_e':round(e['log_e'],8),
                'e_value':None if e['e_value'] is None else round(e['e_value'],8),
                'threshold_log_e':round(threshold,8),
                'evidence_threshold_crossed':crosses,
                'verified_prefix':len(prefix),'total_commits':len(rows),
                'pending_or_after_gap':len(rows)-len(prefix),
                'hits_in_prefix':sum(x['hit'] for x in prefix),
                'expected_hits_fair':sum(x['k']/N for x in prefix),
                'record_hash_integrity':valid,'invalid_records':bad_hashes,
                'alpha_weight':model['alpha_weight'],
                'predictive_edge_proven':False,
                'comment':'过门槛仅说明在强前提条件下拒绝公平随机基线；不保证未来命中或证明选定模型有持续预测优势',
                'assumptions':['真实开奖前封存并具有可信第三方时间证明','全部预先登记结果按顺序完整结算',
                               '公平条件下每个5位号码等概率且不同期独立','注册的模型族与分配规则没有事后更改']}

    def family_report(self):
        models=self.db.execute('SELECT model_id FROM v09_models ORDER BY seq').fetchall()
        reports=[self.model_report(x['model_id']) for x in models]
        return {'family_alpha_total':ALPHA,'models_registered':len(reports),
                'alpha_spent':sum(r['alpha_allocated'] for r in reports),
                'mathematical_budget_not_exceeded':sum(r['alpha_allocated'] for r in reports)<=ALPHA+1e-12,
                'models':reports,'any_crossing':any(r['evidence_threshold_crossed'] for r in reports),
                'claims_not_allowed':['不能将研究性分数解释成校准后的单注中奖概率',
                   '不能保证100注内10期必中','不得把本地未公证封存当作真实赛前证明',
                   '不能跳过失败或未结算实验进行选择性展示']}
