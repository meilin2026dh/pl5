"""多空间并行、规则竞争、映射稳健性 (V0.4)。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pailie5.data import load_csv
from pailie5.pattern_rules import PATTERN_CN, indicator_table
from pailie5.space_mapping import SPACES, register_space_indicators
from pailie5.multispace import multi_space_study, competition_backtest, DISPLAY, select_indicators
from pailie5.mapping_robustness import robustness_study, BASE_METRICS

st.set_page_config(page_title='PL5 · 多空间规则竞争',layout='wide')
st.title('PL5 · 多空间研究、规则竞争与稳健性检验')
st.caption('V0.4 | PL5、23选6、41选4、11位310并行 | 规则去冗余 | 映射对照 | 全10万注排序')
st.warning('反延续规则属于用户设定的启发式筛选偏好。历史出现模式并不会降低公平独立开奖时该模式再次出现的概率。')

upload=st.file_uploader('导入已从官方渠道核验的开奖CSV（period,number）',type=['csv'],key='v04_upload')
demo=st.checkbox('演示模式（伪随机数据，非真实开奖）',value=upload is None,key='v04_demo')
if not demo and upload is None:
    st.info('请导入经官方核对的CSV，或勾选演示模式。')
    st.stop()
try:
    content=((Path(__file__).resolve().parents[1]/'data'/'synthetic_demo.csv').read_bytes()
             if demo else upload.getvalue())
    dataset=load_csv(content,is_demo=demo)
    history=dataset.frame['number'].tolist()
    st.caption(f'已加载 {len(history)} 期开奖。'+'；'.join(dataset.warnings))
except (OSError,ValueError) as exc:
    st.error(f'读取失败：{exc}')
    st.stop()

register_space_indicators()
all_spaces=list(DISPLAY)
st.subheader('① 多空间并行研究')
spaces=st.multiselect('并行选择空间',all_spaces,default=all_spaces,
                      format_func=lambda x:DISPLAY[x])
if not spaces:
    st.info('请至少启用一个空间')
    st.stop()
choice={}
for sp in spaces:
    if sp=='pl5':
        options=['sum','span','odd_count','unique_count','adjacent_equal','digit_1','digit_5']
    else:
        options=list(BASE_METRICS[SPACES[sp].kind])
    # 使用默认的三种不同类型特征；后续由用户控制。
    choice[sp]=tuple(st.multiselect(f'{DISPLAY[sp]} · 指标',options,
                   default=options[:3],key='ms_'+sp))
left,right=st.columns(2)
with left:
    windows=st.multiselect('最近多少期构成规律',list(range(3,13)),default=[3,4])
    transforms=st.multiselect('变换',['raw','mod2','mod3','mod5','mod10'],default=['raw'])
with right:
    patterns=st.multiselect('反延续模式',list(PATTERN_CN),
                           default=['constant','strict_up','strict_down','arithmetic','period2'],
                           format_func=lambda x:PATTERN_CN[x])
    max_rules=st.number_input('参与排序的最多规则数',min_value=1,max_value=120,value=35,step=1)
strength=st.slider('相对评分惩罚强度（非真实中奖概率）',0.0,8.0,1.0,0.25)

state_key=repr((tuple(history),tuple((k,v) for k,v in choice.items()),
                tuple(windows),tuple(patterns),tuple(transforms),max_rules,strength))
if st.button('运行多空间并行研究、规则竞争和全号码排序',type='primary'):
    if not any(choice.values()) or not windows or not patterns or not transforms:
        st.error('至少选择一个指标、窗口、模式和变换。')
    else:
        try:
            with st.spinner('计算空间指标、模式、规则交集和十万注排名…'):
                out=multi_space_study(history,choice,windows=tuple(sorted(windows)),
                     patterns=tuple(patterns),transforms=tuple(transforms),
                     strength=strength,max_rules=int(max_rules))
            st.session_state['v04_parallel']=(state_key,out)
        except Exception as exc:
            st.error(f'研究失败：{exc}')

saved=st.session_state.get('v04_parallel')
if saved and saved[0]==state_key:
    out=saved[1]
    s=out.competition
    a,b,c=st.columns(3)
    a.metric('启用规则',out.metadata['accepted_rules'])
    b.metric('多空间排除并集',f"{s['total_union_removed']:,}")
    c.metric('并集覆盖率',f"{s['total_union_coverage']:.2%}")
    st.subheader('最近历史各空间指标')
    st.dataframe(out.history_table.tail(15),hide_index=True,use_container_width=True)
    st.subheader('② 规则竞争与重复证据诊断')
    st.caption('边际排除数依固定规则顺序计算；规则间重合越高，越不应重复计作独立证据。')
    st.dataframe(out.rule_table,hide_index=True,use_container_width=True)
    st.markdown('**空间汇总**')
    st.dataframe(pd.DataFrame([{'space':key,**value} for key,value in s['per_space'].items()]),
                 hide_index=True,use_container_width=True)
    st.markdown('**空间之间覆盖重叠（Jaccard / Phi）**')
    st.dataframe(pd.DataFrame(s['space_overlap']),hide_index=True,use_container_width=True)
    st.markdown('**重复程度较高的规则对（最多显示60组）**')
    st.dataframe(pd.DataFrame(s['top_rule_overlaps']),hide_index=True,use_container_width=True)
    st.subheader('10万注统一启发式排名')
    st.dataframe(out.table.head(100),hide_index=True,use_container_width=True)
    st.caption('model_weight是归一化的主观启发式权重，**不是**经过验证的真实中奖概率。')
    st.download_button('下载完整十万注CSV',out.table.to_csv(index=False).encode('utf-8-sig'),
                       'PL5_v04_多空间全量评分.csv','text/csv')
    summary={'metadata':out.metadata,'competition':out.competition,
             'rule_details':out.rule_table.to_dict(orient='records')}
    st.download_button('下载竞争分析JSON',json.dumps(summary,ensure_ascii=False,indent=2).encode('utf-8'),
                       'PL5_v04_竞争报告.json','application/json')

st.divider()
st.subheader('③ 多空间/多规则逐期竞争回测')
st.caption('只用当前开奖之前的历史生成规则，记录每个指标模式的条件命中与随机基线对照。')
max_periods=st.slider('回测最近多少期',3,40,12,key='competition_periods')
warmup_c=st.number_input('规则竞争回测最少热身期数',min_value=12,max_value=1000,value=40,key='competition_warmup')
bk=repr((tuple(history),tuple((k,v) for k,v in choice.items()),tuple(windows),tuple(patterns),
         tuple(transforms),max_rules,max_periods,warmup_c))
if st.button('运行逐期规则竞争回测'):
    if not any(choice.values()) or not windows or not patterns or not transforms:
        st.error('请配置至少一个可用的空间指标及窗口、模式、变换。')
    else:
        try:
            with st.spinner('逐期计算原始及映射空间规则…'):
                bkout=competition_backtest(history,choice,windows=tuple(sorted(windows)),
                    patterns=tuple(patterns),transforms=tuple(transforms),
                    max_rules=int(max_rules),warmup=int(warmup_c),max_periods=max_periods)
            st.session_state['v04_backtest']=(bk,bkout)
        except Exception as exc:
            st.error(f'回测失败：{exc}')
bs=st.session_state.get('v04_backtest')
if bs and bs[0]==bk:
    bkout=bs[1]
    st.markdown('**分空间逐期覆盖**')
    st.dataframe(pd.DataFrame(bkout['per_space']),hide_index=True,use_container_width=True)
    st.markdown('**分指标 × 模式 × 窗口历史表现**')
    st.dataframe(pd.DataFrame(bkout['per_rule']),hide_index=True,use_container_width=True)
    st.info(bkout['note'])
    st.download_button('下载滚动回测报告JSON',json.dumps(bkout,ensure_ascii=False,indent=2).encode(),
                       'PL5_v04_规则竞争滚动回测.json','application/json')

st.divider()
st.subheader('④ 映射稳健性检验（预固定对照 + 同期滚动回测）')
st.caption('原始空间本身不参与映射安慰剂实验；此处仅检验不同可逆编码参数是否使结果剧烈变化。')
r1,r2=st.columns(2)
with r1:
    target=st.selectbox('检验映射空间',list(SPACES),format_func=lambda x:SPACES[x].label)
    metrics=st.multiselect('检验的空间指标',BASE_METRICS[SPACES[target].kind],
                           default=list(BASE_METRICS[SPACES[target].kind])[:2],key='robust_'+target)
    lookback=st.slider('检测窗口（期）',3,12,4)
    n_variants=st.slider('预固定映射数量（含正式映射）',2,8,5)
with r2:
    top_k=st.select_slider('检验前K名覆盖',options=[100,500,1000,2000,5000,10000],value=1000)
    holdout=st.number_input('最多回测多少期',min_value=3,max_value=100,value=15)
    warmup=st.number_input('起始最少历史期数',min_value=12,max_value=1000,value=40)
    seed=st.text_input('固定对照种子（实验开始前预注册）','pl5-v04-fixed-baseline')

rk=repr((tuple(history),target,tuple(metrics),lookback,n_variants,top_k,holdout,warmup,seed))
if st.button('运行映射安慰剂检验'):
    if not metrics:
        st.error('请选择至少一个指标')
    else:
        try:
            with st.spinner('按相同期号对多个固定映射进行前向回测…'):
                report=robustness_study(history,target,tuple(metrics),window=lookback,
                         variant_count=n_variants,seed=seed,top_k=top_k,
                         holdout=holdout,warmup=warmup)
            st.session_state['v04_robust']=(rk,report)
        except Exception as exc:
            st.error(f'稳健性检验失败：{exc}')

rs=st.session_state.get('v04_robust')
if rs and rs[0]==rk:
    report=rs[1]
    st.dataframe(pd.DataFrame(report['variants']),hide_index=True,use_container_width=True)
    st.caption(f"相同的{report['variants'][0]['periods']}期前向测试，每种映射随机基线预期命中"
               f" {report['variants'][0]['fair_expected_hits']:.2f}期。");
    st.markdown('**当前被反延续规则标记的集合与对照映射的相似度**')
    st.dataframe(pd.DataFrame(report['current_set_overlap']),hide_index=True,use_container_width=True)
    st.info(report['note'])
    st.download_button('下载映射稳健性实验JSON',
                       json.dumps(report,ensure_ascii=False,indent=2).encode(),
                       'PL5_v04_映射稳健性报告.json','application/json')
