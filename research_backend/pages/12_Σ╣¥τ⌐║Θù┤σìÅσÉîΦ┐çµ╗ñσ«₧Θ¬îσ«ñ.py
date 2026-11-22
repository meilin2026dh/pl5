"""V2.4 nine-space filter workbench. Experimental, never a probability forecast."""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from pailie5.nine_spaces_v24 import (
    FAMILIES, TEMPORAL_FAMILIES, Rule, TemporalSpec, Spaces,
    capability_cards, compose_temporal, walk_forward_temporal,
)

st.set_page_config(page_title='PL5 · 九空间协同研究',layout='wide')
st.title('九空间特征与协同过滤实验室')
st.caption('探索性指标研究；任何过滤规则都不自动代表中奖概率优势。保留前导零，候选集大小决定公平随机覆盖率。')

@st.cache_data(show_spinner=False)
def parse_history(raw:bytes):
    text=raw.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or 'number' not in reader.fieldnames:
        raise ValueError('历史CSV需包含number列；建议issue,date,number')
    rows=list(reader)
    if not rows:raise ValueError('历史数据为空')
    for field in ('issue','period','date'):
        if field in reader.fieldnames and len({r[field] for r in rows})!=len(rows):
            raise ValueError(f'重复{field}')
    key='date' if 'date' in reader.fieldnames else ('period' if 'period' in reader.fieldnames else 'issue' if 'issue' in reader.fieldnames else '')
    if key:rows.sort(key=lambda x:x[key])
    history=[row['number'] for row in rows]
    Spaces(history)
    return history

src=st.file_uploader('导入已核验的官方历史CSV（数据来源须自行核实）',type=['csv'])
if src is None:
    st.info('请先导入历史数据。可浏览算法能力说明，但当前不会使用合成数据伪装官方开奖。')
    hist=[]
else:
    try:hist=parse_history(src.getvalue())
    except Exception as e: st.error(str(e)); st.stop()

with st.expander('九类算法能力说明书',expanded=False):
    st.dataframe([{'ID':v['id'],'能力':v['name'],'预测状态':'尚未验证'} for v in capability_cards()],hide_index=True)

st.subheader('一、选择指标与过滤条件')
if 'v24_static_rules' not in st.session_state:st.session_state.v24_static_rules=[]
if 'v24_temporal_specs' not in st.session_state:st.session_state.v24_temporal_specs=[]
family=st.selectbox('特征空间',list(FAMILIES),format_func=lambda k:FAMILIES[k] if k!='intersection' else '集合交集（由协同模块执行）')
if family=='intersection': st.info('交集为组合器，不含直接可比较的单项指标'); st.stop()
try:
    features=Spaces(hist).get(family)
except ValueError as e:
    st.warning(str(e)); st.stop()
metric=st.selectbox('指标',list(features))
col1,col2,col3=st.columns(3)
with col1: operator=st.selectbox('比较方式',['eq','ne','gt','ge','lt','le','between','in','not_in'])
with col2: value=st.text_input('指标数值（between用a,b；in用a,b,c）','0')
with col3: action=st.selectbox('满足条件时',['过滤该值','仅保留该值'])

def read_value(text,op):
    parts=[x.strip() for x in text.split(',') if x.strip()]
    if not parts:raise ValueError('至少输入一个数值')
    values=[float(x) for x in parts]
    if op in ('between','in','not_in'):
        if op=='between' and len(values)!=2:raise ValueError('between需要恰好两项')
        return values
    if len(values)!=1: raise ValueError('单值比较需要恰好一项')
    return values[0]

if st.button('加入静态规则'):
    try:
        r=Rule(f'ui-rule-{len(st.session_state.v24_static_rules)+1}',family,metric,operator,
               read_value(value,operator),'exclude' if action=='过滤该值' else 'retain')
        Spaces(hist).mask(r)
        st.session_state.v24_static_rules.append(r)
    except Exception as e:st.error(str(e))

st.subheader('二、最近N期模式反延续')
c1,c2,c3=st.columns(3)
with c1: temporal_pattern=st.selectbox('历史模式',['repeat','arithmetic','alternating','periodic'])
with c2: temporal_window=st.number_input('观察期数',min_value=2,max_value=30,value=4,step=1)
with c3: temporal_period=st.number_input('周期',min_value=2,max_value=10,value=2,step=1)
if st.button('加入时序研究规则'):
    try:
        spec=TemporalSpec(f'ui-temporal-{len(st.session_state.v24_temporal_specs)+1}',family,metric,
                          int(temporal_window),temporal_pattern,int(temporal_period))
        st.session_state.v24_temporal_specs.append(spec)
    except Exception as e:st.error(str(e))

if st.session_state.v24_static_rules or st.session_state.v24_temporal_specs:
    st.json({'static_rules':[r.__dict__ for r in st.session_state.v24_static_rules],
             'temporal_specs':[s.__dict__ for s in st.session_state.v24_temporal_specs]})
if st.button('清空规则'):
    st.session_state.v24_static_rules=[]
    st.session_state.v24_temporal_specs=[]
    st.rerun()

st.subheader('三、全集组合及历史回测')
c1,c2,c3=st.columns(3)
with c1:budget=st.number_input('目标注数（研究候选）',min_value=1,max_value=100,value=100)
with c2:seed=st.number_input('随机同分排序种子',min_value=0,max_value=4294967295,value=42)
with c3:window=st.number_input('最多使用历史期数',min_value=3,max_value=10000,value=100)

if st.button('计算10万注并生成研究报告',type='primary'):
    try:
        selected=hist[-int(window):]
        out=compose_temporal(selected,st.session_state.v24_static_rules,st.session_state.v24_temporal_specs,
                            budget=int(budget),seed=int(seed))
        st.session_state.v24_last=out
    except Exception as e:st.error(str(e))

if st.session_state.get('v24_last'):
    out=st.session_state.v24_last
    a,b,c=st.columns(3)
    a.metric('严格规则剩余',f"{out['strict_remaining']:,}")
    b.metric('Top-K研究候选',len(out['ranked_numbers']))
    c.metric('公平随机Top-K覆盖率',f"{100*out['ranked_exact_random_coverage']:.4f}%")
    st.dataframe(out['audit'],hide_index=True)
    if out.get('temporal_proposals'):st.json(out['temporal_proposals'])
    st.download_button('下载研究报告JSON',json.dumps(out,ensure_ascii=False,indent=2),file_name='pl5_v24_report.json')
    st.download_button('下载Top-K CSV','number\n'+'\n'.join(out['ranked_numbers'])+'\n',file_name='pl5_v24_topk.csv')

if hist:
    periods=st.number_input('回测期数',min_value=1,max_value=min(100,len(hist)-1),value=min(10,len(hist)-1))
    if st.button('逐期独立回测（每期只使用之前已公布数据）'):
        try:
            result=walk_forward_temporal(hist[-max(int(window),int(periods)+30):],
                st.session_state.v24_static_rules, st.session_state.v24_temporal_specs,
                last_n=int(periods),min_train=30,budget=int(budget),seed=int(seed))
            st.json({k:v for k,v in result.items() if k!='rows'})
            st.dataframe(result['rows'],hide_index=True)
        except Exception as e:st.error(str(e))
