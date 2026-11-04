"""PL5第三个独立页面：跨空间编码、审计及反延续过滤/排序实验。"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st

from pailie5.data import load_csv
from pailie5.space_mapping import SPACES, encoding_of, inverse_encoding, mapping_coverage, register_space_indicators
from pailie5.pattern_rules import Configuration, PATTERN_CN, filter_next, historical_indicators
from pailie5.probability_ranker import rank_all_numbers, rule_key

LABELS=register_space_indicators()

st.title('PL5 · 跨空间映射实验室')
st.caption('V0.3 跨空间：PL5号码 → 23选6 / 41选4 / 11位310 → 映射指标 → 时序反延续 → 全量排序')
st.warning('改变表示空间不会改变公平开奖下每注0.001%的真实概率。映射后的特殊模式仅是待验证的实验假设。')

space=st.selectbox('选择编码空间',list(SPACES),format_func=lambda x:SPACES[x].label)
cov=mapping_coverage(space)
a,b,c=st.columns(3)
a.metric('目标空间状态数',f'{cov["target_size"]:,}')
b.metric('已映射排列五号码','100,000')
c.metric('未分配组合数',f'{cov["unmapped"]:,}')
st.caption('严格一一映射：'+cov['mapping_version']+'；未分配的目标组合不能误当成排列五号码。')

number=st.text_input('查看指定号码的跨空间编码（保留前导零）','00128',max_chars=5)
try:
    encoded=encoding_of(number,space)
    recovered=inverse_encoding(encoded,space)
    st.code(f'PL5 {number}  →  {SPACES[space].label} [{encoded}]  →  PL5 {recovered}',language='text')
except (ValueError,TypeError) as exc:
    st.warning(str(exc))

upload=st.file_uploader('上传核验后的历史开奖CSV：period,number',type=['csv'],key='cross_csv')
demo=st.checkbox('使用合成数据演示（非官方）',value=upload is None,key='cross_demo')
if not demo and upload is None:
    st.info('上传官方核验的CSV后即可检测模式。')
    st.stop()

try:
    raw=(Path(__file__).resolve().parents[1]/'data'/'synthetic_demo.csv').read_bytes() if demo else upload.getvalue()
    draws=load_csv(raw,is_demo=demo)
    history=draws.frame['number'].tolist()
except Exception as exc:
    st.error(f'开奖数据读取失败：{exc}')
    st.stop()

available={key:label for key,label in LABELS.items() if key.startswith(space+'__')}
selected=st.multiselect('选择映射后的指标',list(available),format_func=lambda x:available[x],
                        default=list(available)[:3])
windows=st.multiselect('观察最近多少期',list(range(3,13)),default=[3,4,6])
patterns=st.multiselect('寻找哪些历史模式',list(PATTERN_CN),
                        default=['constant','strict_up','strict_down','arithmetic','period2'],
                        format_func=lambda x:PATTERN_CN[x])
transforms=st.multiselect('指标变换',['raw','mod2','mod3','mod5','mod10'],default=['raw'])
strength=st.slider('模式反延续惩罚强度（不是中奖概率）',0.0,4.0,1.0,0.25)
if not all([selected,windows,patterns,transforms]):
    st.info('请至少选一个指标、历史窗口、模式和变换。')
    st.stop()
cfg=Configuration(indicators=tuple(selected),windows=tuple(sorted(windows)),
                  patterns=tuple(patterns),transforms=tuple(transforms),
                  max_rule_remove=.65,max_total_remove=.8, min_keep=1000)
st.subheader('最近开奖的跨空间指标序列')
recent=historical_indicators(history,tuple(selected))[-max(windows)-3:]
st.dataframe(pd.DataFrame(recent).rename(columns=LABELS),hide_index=True,use_container_width=True)

key=(tuple(history),cfg,space)
if st.button('探测跨空间历史模式',type='primary'):
    result=filter_next(history,cfg)
    st.session_state['cross_detect']={'key':key,'summary':result.summary(),'rules':result.rules}
    st.session_state.pop('cross_rank',None)

found=st.session_state.get('cross_detect')
if found and found['key']==key:
    rules=found['rules']
    st.subheader('检测结果及规则选择')
    st.caption(f'检测到{len(rules)}种去重后的模式；可手动选择要参与排序的规则。')
    keys={rule_key(r):(f'{LABELS.get(r.indicator,r.indicator)} · {PATTERN_CN[r.pattern]} · 最近{r.window}期 '
                             f'· 历史{r.observed} · 待避开值{r.banned_values} · 单规则覆盖{r.raw_removed_rate:.1%}')
          for r in rules}
    chosen=st.multiselect('选择参与评分的模式',list(keys),format_func=lambda k:keys[k],
                          default=[rule_key(r) for r in rules if r.status=='applied'])
    if st.button('计算全部10万号码的跨空间评分与排名'):
        output=rank_all_numbers(history,cfg,strength=strength,selected_rule_keys=chosen)
        st.session_state['cross_rank']={'key':key,'chosen':tuple(chosen),'strength':strength,'out':output}
    ranked=st.session_state.get('cross_rank')
    if ranked and ranked['key']==key and ranked['chosen']==tuple(chosen) and ranked['strength']==strength:
        out=ranked['out']
        st.subheader('十万注相对评分排名')
        st.caption('model_probability是启发式软最大归一化分数，不是经过验证的中奖概率。')
        st.dataframe(out.table.head(100),hide_index=True,use_container_width=True)
        st.download_button('导出十万注完整排名CSV',out.table.to_csv(index=False).encode('utf-8-sig'),
                           'pl5_跨空间10万排名.csv','text/csv')
        st.download_button('导出规则及模型解释JSON',json.dumps({'metadata':out.metadata,'rules':out.rule_details},
             ensure_ascii=False,indent=2).encode(),'pl5_跨空间规则报告.json','application/json')

st.info('注意：同一映射的多个指标高度相关；跨空间得分属于实验性特征，未来应使用映射置换对照与严格样本外回测验证。')
