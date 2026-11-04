"""V0.2真正的可恢复工作流：LangGraph选装，默认可离线确定性执行。"""
from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from typing import TypedDict, Any
from scipy.stats import binomtest
from .data import Draws
from .knowledge import KnowledgeBase, fingerprint, holdout_key
from .discovery import (template_hypotheses, generated_blends, llm_hypotheses,
                        validate_spec, evaluate, select_by_development)

class ResearchState(TypedDict, total=False):
    params: dict
    dataset_sha: str
    lock_key: str
    proposals: list[dict]
    llm_note: str
    dev_evaluations: list[dict]
    chosen: dict | None
    preregistration: dict
    experiment_id: int
    holdout_metrics: dict
    report: dict


class ResearchAgent:
    def __init__(self, draws: Draws, kb: KnowledgeBase):
        self.draws=draws
        self.kb=kb

    def validate(self, state: ResearchState) -> dict:
        p=state['params']
        n=len(self.draws.frame)
        if not (1<=p['count']<=100_000 and p['window']>=20 and
                p['min_train']>=20 and p['dev_size']>=10 and p['holdout_size']>=10):
            raise ValueError('实验参数不合法；开发和封存测试集均至少10期')
        if p['min_train']+p['dev_size']+p['holdout_size']>n:
            raise ValueError(f'数据不足：至少需要{p["min_train"]+p["dev_size"]+p["holdout_size"]}期，目前{n}期')
        key=holdout_key(self.draws,p['holdout_size'])
        existing=self.kb.get_experiment(key)
        if existing:
            raise ValueError('测试集已经开封或正在执行。为防止重复调参，不允许同一数据和封存区间重复检验。'
                             f'原实验ID={existing["id"]}；请使用未来新开奖数据开启新的验证周期。')
        return {'dataset_sha':fingerprint(self.draws),'lock_key':key}

    def propose(self, state: ResearchState) -> dict:
        models=template_hypotheses()
        note='内置受限模板自动提案（离线，不调用语言模型）'
        if state['params'].get('llm'):
            suggestions,note=llm_hypotheses(model=state['params'].get('llm_model','gpt-5.5'))
            models.extend(suggestions)
        models.extend(generated_blends(state['params']['seed']))
        unique={}
        for s in models:
            v=validate_spec(s)
            key=json.dumps({k:v[k] for k in sorted(v) if k!='name'},sort_keys=True,ensure_ascii=False)
            unique.setdefault(key,v)
        return {'proposals':list(unique.values())[:7],'llm_note':note}

    def develop(self, state: ResearchState) -> dict:
        p=state['params'];n=len(self.draws.frame)
        dev_end=n-p['holdout_size'];dev_start=dev_end-p['dev_size']
        evaluation=[]
        for spec in state['proposals']:
            metrics=evaluate(self.draws,indices=range(dev_start,dev_end),spec=spec,
                             k=p['count'],window=p['window'],seed=p['seed'])
            evaluation.append({'name':spec['name'],'spec':spec,'metrics':metrics})
        chosen,results=select_by_development(evaluation,alpha=p['dev_alpha'])
        return {'dev_evaluations':results,'chosen':chosen}

    def preregister(self, state: ResearchState) -> dict:
        p=state['params']
        n=len(self.draws.frame)
        # 在此处写入数据库并锁住封存集，之后的节点才可以读取末尾的真实号码。
        frozen={
          'dataset_sha':state['dataset_sha'],
          'holdout_size':p['holdout_size'], 'holdout_start_index':n-p['holdout_size'],
          'dev_size':p['dev_size'],'count':p['count'],'seed':p['seed'],
          'window':p['window'],'min_train':p['min_train'],'dev_alpha':p['dev_alpha'],
          'chosen':state['chosen'],'all_proposals':state['proposals'],
          'llm_note':state['llm_note'],
          'no_raw_code_execution':True,
          'research_only':True
        }
        expid=self.kb.preregister(
            key=state['lock_key'],dataset_sha=state['dataset_sha'],prereg=frozen,
            dev={'evaluations':state['dev_evaluations']})
        return {'preregistration':frozen,'experiment_id':expid}

    def open_holdout(self, state: ResearchState) -> dict:
        p=state['params'];n=len(self.draws.frame)
        metrics=evaluate(self.draws,indices=range(n-p['holdout_size'],n),
                         spec=state['chosen'],k=p['count'],window=p['window'],seed=p['seed'])
        # 固定候选集合规模的公平随机基线; 二项检验只做一次开封。
        pv=float(binomtest(metrics['hits'],metrics['periods'],p['count']/100_000,
                           alternative='greater').pvalue)
        if state['chosen'] is None:
            status='baseline_only_no_dev_evidence'
        elif pv < 0.01 and metrics['mean_log_gain']>0:
            status='exploratory_signal_requires_replication'
        else:
            status='no_verified_advantage'
        metrics.update({'binomial_p':pv,'status':status,
                        'chosen':state['chosen'],
                        'theoretical_cover_rate':p['count']/100_000})
        return {'holdout_metrics':metrics}

    def audit(self, state: ResearchState) -> dict:
        info=state['holdout_metrics']
        expid=self.kb.finalize_experiment(key=state['lock_key'],holdout=info,
                                           hypothesis_rows=state['dev_evaluations'])
        report={
           'version':'0.2.0','experiment_id':expid,'data_is_demo':self.draws.is_demo,
           'dataset_sha256':state['dataset_sha'],
           'total_periods':len(self.draws.frame),
           'preregistration':state['preregistration'],
           'development':state['dev_evaluations'],
           'holdout':info,
           'notes':[
             '测试集在数据库预注册后才打开；第二次开封会被阻断。',
             '开发集选择仅依靠开发集历史，封存集没有参与选模型。',
             '封存集使用逐期推进：允许使用测试集中已开奖的更早期结果更新历史窗口，但不据此改选模型。',
             '随机公平基线：保留K注的覆盖率为K/100000。',
             '开发集多模型测试做Bonferroni校正；跨研究和人工择优仍可能导致选择偏差。',
             '如无证据，选择纯随机对照，而非宣称能够预测。',
             '用户上传CSV只表示声明来源，程序无法独立鉴定开奖公告真伪。',
             '不包含自动投注、账户访问或任何资金操作。'
           ]
        }
        return {'report':report}

    def run(self, *, count=1000, dev_size=40,holdout_size=40,window=500,
            min_train=100,seed=42,dev_alpha=0.01,llm=False,llm_model='gpt-5.5',
            use_langgraph='auto', checkpoint_path: str | Path | None=None):
        params=dict(count=int(count),dev_size=int(dev_size),holdout_size=int(holdout_size),
                    window=int(window),min_train=int(min_train),seed=int(seed),
                    dev_alpha=float(dev_alpha),llm=bool(llm),llm_model=llm_model)
        nodes=[('validate',self.validate),('propose',self.propose),
               ('develop',self.develop),('preregister',self.preregister),
               ('open_holdout',self.open_holdout),('audit',self.audit)]
        initial={'params':params}
        if use_langgraph not in ('auto','required','off'):
            raise ValueError('use_langgraph应为auto/required/off')
        if use_langgraph != 'off':
            try:
                from langgraph.graph import StateGraph, START, END
                from langgraph.checkpoint.sqlite import SqliteSaver
            except ImportError:
                if use_langgraph=='required':
                    raise RuntimeError('未安装LangGraph扩展：运行 uv sync --extra agent 后再试')
            else:
                os.environ.setdefault('LANGGRAPH_STRICT_MSGPACK','true')
                graph=StateGraph(ResearchState)
                for name,node in nodes: graph.add_node(name,node)
                graph.add_edge(START,nodes[0][0])
                for a,b in zip(nodes,nodes[1:]): graph.add_edge(a[0],b[0])
                graph.add_edge(nodes[-1][0],END)
                cp=Path(checkpoint_path or self.kb.path.with_name('agent_checkpoints.sqlite'))
                with SqliteSaver.from_conn_string(str(cp)) as saver:
                    app=graph.compile(checkpointer=saver)
                    state=app.invoke(initial,config={'configurable':{'thread_id':str(uuid.uuid4())}})
                    return state['report']
        state=initial
        for _,node in nodes:
            state={**state,**node(state)}
        return state['report']
