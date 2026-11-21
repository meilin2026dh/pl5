"""受限假设语言：自动生成候选模型规格而不执行LLM生成的代码。"""
from __future__ import annotations
import json
import os
import numpy as np
from scipy.special import logsumexp
from scipy.stats import norm
from .engine import score_candidates, DIGITS, UNIVERSE

SAFE_TYPES = {'positional', 'pairwise', 'ensemble', 'recency', 'blend'}


def validate_spec(spec: dict) -> dict:
    if not isinstance(spec,dict) or spec.get('type') not in SAFE_TYPES:
        raise ValueError('未知算法类型，已拒绝')
    algo = spec['type']
    # 只允许DSL中的白名单字段，避免把任意代码作为模型执行。
    allowed = ({'type','half_life','name'} if algo == 'recency' else
               {'type','components','weights','name'} if algo == 'blend' else {'type','name'})
    if set(spec) - allowed:
        raise ValueError('包含未授权的算法字段')
    if algo == 'recency':
        half_life = spec.get('half_life')
        if type(half_life) is not int or not 25 <= half_life <= 300:
            raise ValueError('recency半衰期要求25～300之间的整数')
    if algo=='blend':
        parts=spec.get('components'); weights=spec.get('weights')
        if not isinstance(parts,list) or not 2<=len(parts)<=3 or not isinstance(weights,list) or len(weights)!=len(parts):
            raise ValueError('融合模型要求2～3个已批准组件及对应权重')
        if any(type(w) is not int or not 1<=w<=5 for w in weights):
            raise ValueError('融合权重必须是1～5的整数')
        for part in parts:
            if not isinstance(part,dict) or part.get('type') not in SAFE_TYPES-{'blend'}:
                raise ValueError('禁止嵌套融合或未知组件')
            validate_spec(part)
    name = spec.get('name',algo)
    if not isinstance(name,str) or len(name)>70 or not name.strip():
        raise ValueError('算法名称非法')
    return dict(spec)


def template_hypotheses() -> list[dict]:
    return [
        {'name':'位置频率偏差','type':'positional'},
        {'name':'二位置联合偏差','type':'pairwise'},
        {'name':'模型融合','type':'ensemble'},
        {'name':'近期加权半衰期50','type':'recency','half_life':50},
        {'name':'近期加权半衰期150','type':'recency','half_life':150},
    ]


def generated_blends(seed: int = 42) -> list[dict]:
    """受限DSL自动组合（符号程序合成），生成新评分组合但不执行新代码。"""
    rng = np.random.default_rng(seed)
    candidates = [
      [{'type':'positional'}, {'type':'recency','half_life':80}],
      [{'type':'pairwise'}, {'type':'recency','half_life':100}],
      [{'type':'positional'}, {'type':'pairwise'}, {'type':'recency','half_life':60}],
      [{'type':'ensemble'}, {'type':'recency','half_life':250}],
    ]
    choices = rng.choice(len(candidates),size=2,replace=False)
    return [validate_spec({'name':f'DSL自动合成-{j+1}', 'type':'blend',
                           'components':candidates[int(idx)],
                           'weights':[int(v) for v in rng.integers(1,4,len(candidates[int(idx)]))]})
            for j,idx in enumerate(choices)]


def llm_hypotheses(*, model='gpt-5.5', limit=2) -> tuple[list[dict],str]:
    """可选外部LLM仅生成受限JSON参数。API缺失或出错时不阻断程序。"""
    if not os.getenv('OPENAI_API_KEY'):
        return [], '未配置OPENAI_API_KEY，使用本地模板自动提案'
    try:
        from openai import OpenAI
        c = OpenAI(timeout=18.0)
        result = c.responses.create(
            model=model,
            instructions=(
                '你是统计假设研究助理。公平独立彩票不可预测。只能输出一个JSON数组，最多2条。'
                '每条为{"type":"recency","half_life":25到300整数,"name":"简短名称"}。'
                '你的任务是提出可证伪的实验设定，不准声称能提高中奖率。'
                '不得生成可执行代码。'),
            input='给出两个不同的受限时序衰减统计实验假设。'
        )
        output = result.output_text.strip()
        if output.startswith('```'):
            output = output.split('\n',1)[-1].rsplit('```',1)[0].strip()
        proposals = json.loads(output)
        if not isinstance(proposals,list):
            raise ValueError('模型输出不是列表')
        checked = [validate_spec(x) for x in proposals[:limit]]
        return checked, '模型仅提出受限JSON参数，由本地确定性代码执行；未执行生成代码'
    except Exception as exc:
        return [], f'语言模型不可用：{type(exc).__name__}；已回退内置假设'


def score_spec(history: list[str], spec: dict) -> np.ndarray:
    spec=validate_spec(spec)
    if spec['type']=='blend':
        combined=np.zeros(100_000,dtype=np.float64)
        for part,weight in zip(spec['components'],spec['weights']):
            values=score_spec(history,part)
            sd=values.std()
            if sd>1e-12:
                combined+=weight*(values-values.mean())/sd
        return combined / sum(spec['weights'])
    if spec['type'] != 'recency':
        return score_candidates(history, spec['type'])
    arr = np.asarray([[int(v) for v in s] for s in history], dtype=np.int16)
    if arr.ndim != 2 or arr.shape[1] != 5:
        raise ValueError('历史数据格式错误')
    hl=spec['half_life']
    age=np.arange(len(arr)-1,-1,-1,dtype=np.float64)
    w=np.exp2(-age/hl)
    scores=np.zeros(100_000,dtype=np.float64)
    for p in range(5):
        sums=np.bincount(arr[:,p],weights=w,minlength=10)
        probs=(sums+1.0)/(w.sum()+10.0)
        scores += np.log(probs[DIGITS[:,p]])/5.0
    return scores


def step_metrics(history: list[str], actual: str, spec: dict | None, *, k: int, seed: int):
    """返回单步log增益（相对于均匀分布）与保留K注的命中与否。"""
    target=int(actual)
    rng=np.random.default_rng(seed)
    if spec is None:
        chosen=rng.choice(100_000,k,replace=False)
        return 0.0, int(target in chosen)
    scores=score_spec(history,spec)
    gain=float(scores[target] - logsumexp(scores) + np.log(100_000))
    # 通过随机噪声对并列分数随机打散。
    ranks=scores+rng.uniform(0,1e-11,100_000)
    chosen=np.argpartition(-ranks,k-1)[:k]
    return gain, int(target in chosen)


def evaluate(draws, *, indices: range, spec: dict | None, window: int,
             k: int, seed: int) -> dict:
    frame=draws.frame
    diffs=[];hits=0
    for i in indices:
        history=frame['number'].iloc[max(0,i-window):i].tolist()
        gain,hit=step_metrics(history,str(frame['number'].iat[i]),spec,k=k,seed=seed+i*7919)
        diffs.append(gain);hits+=hit
    a=np.asarray(diffs,dtype=np.float64)
    return {'periods':len(a),'hits':int(hits),'baseline_expected_hits':float(len(a)*k/100_000),
            'mean_log_gain':float(a.mean()),'std_log_gain':float(a.std(ddof=1)) if len(a)>1 else 0.0,
            'first_period':str(frame['period'].iat[indices.start]),
            'last_period':str(frame['period'].iat[indices.stop-1])}


def select_by_development(results: list[dict], *, alpha=0.01) -> tuple[dict | None,list[dict]]:
    """一次性检验：模型log增益均值的单侧z检验 + 候选数量Bonferroni。低功效时一律退回随机。"""
    m=max(1,len(results))
    enriched=[]
    for r in results:
        metric=r['metrics']
        n=metric['periods']; avg=metric['mean_log_gain']; sd=metric['std_log_gain']
        p=float(norm.sf(avg/(sd/np.sqrt(n)))) if sd>1e-12 and n>=10 else 1.0
        p_corrected=min(1.0,m*p)
        accepted=bool(avg>0 and p_corrected<alpha)
        enriched.append({**r,'one_sided_p':p,'p_adjusted':p_corrected,
                         'decision':'eligible' if accepted else 'rejected'})
    passing=[x for x in enriched if x['decision']=='eligible']
    if not passing:
        return None,enriched
    winner=max(passing,key=lambda x:x['metrics']['mean_log_gain'])
    for r in enriched:
        r['decision']='selected' if r['name']==winner['name'] else 'rejected'
    return winner['spec'],enriched
