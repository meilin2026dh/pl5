"""可独立执行streamlit run pattern_app.py；也可从V0.2多页面启动。"""
from __future__ import annotations
import io, json
import pandas as pd
import streamlit as st
from pathlib import Path
from pailie5.space_mapping import register_space_indicators
from pailie5.pattern_rules import EXTRA_INDICATORS
SPACE_INDICATOR_LABELS = register_space_indicators()
from pailie5.data import load_csv
from pailie5.pattern_rules import Configuration, PATTERN_CN, filter_next, historical_indicators, rolling_backtest, indicator_table, CONTEXT_INDICATORS
from pailie5.basic_filters import BasicConstraint, combine_basic_and_pattern


def render():
    st.title('PL5 · 指标时序模式实验室')
    st.caption('V0.3研究原型 | 基础过滤 + 历史时序反延续规则 + 严格前向回测')
    st.warning('随机序列同样会出现重复和有序模式。过滤规则是研究假说，不代表后续开奖号码概率变小。')
    up = st.file_uploader('导入官方核验过的历史开奖CSV（期号、开奖号码，保留前导零）', type=['csv'], key='pattern_uploaded')
    demo = st.checkbox('使用合成演示数据（禁止作为正式实验）', value=up is None, key='pattern_demo')
    if not demo and up is None:
        st.info('请上传经过官方核验的CSV，或开启合成演示模式。')
        return
    try:
        path = Path(__file__).parent / 'data' / 'synthetic_demo.csv'
        draws = load_csv(path.read_bytes(), is_demo=True) if demo else load_csv(up.getvalue())
        history = draws.frame['number'].tolist()
        if demo: st.info('使用的是伪随机演示数据；不表示真实开奖结果。')
        for warning in draws.warnings: st.caption(warning)
    except Exception as e:
        st.error(f'输入校验失败：{e}')
        return
    with st.sidebar:
        st.header('指标和模式')
        all_indicators = tuple(indicator_table()) + tuple(CONTEXT_INDICATORS) + tuple(EXTRA_INDICATORS)
        inds = st.multiselect('研究指标',all_indicators,
                   default=['sum','span','odd_count','unique_count','adjacent_equal','digit_5','same_positions_prev'])
        trans = st.multiselect('指标变换', ['raw','mod2','mod3','mod5','mod10'], default=['raw','mod2'])
        patterns = st.multiselect('时序模式',list(PATTERN_CN),default=['constant','strict_up','strict_down','arithmetic','period2','zigzag'])
        wins = st.multiselect('历史窗口长度',list(range(3,9)),default=[3,4,6])
        mode = st.radio('模式触发逻辑', ['continuation','recurrence'], format_func=lambda s: '紧邻模式继续' if s == 'continuation' else '近段内曾出现，防止再次出现')
        lookback=st.slider('回看多少期（再次出现模式）',6,50,15)
        limit=st.slider('单规则最大过滤比例',5,100,60,step=5)/100
        total=st.slider('多规则最大总过滤比例',10,95,80,step=5)/100
        min_keep=st.number_input('模式过滤后最少保留注数',1,100000,1000,step=100)
    if not inds or not trans or not patterns or not wins:
        st.info('至少选择一个指标、变换、模式和窗口。')
        return
    config=Configuration(indicators=tuple(inds),transforms=tuple(trans),patterns=tuple(patterns),windows=tuple(sorted(wins)),
                         mode=mode,lookback=max(lookback,max(wins)),max_rule_remove=limit,
                         max_total_remove=total,min_keep=int(min_keep))
    st.subheader('1. 最近各期指标')
    st.dataframe(pd.DataFrame(historical_indicators(history, tuple(inds))[-20:]),hide_index=True,use_container_width=True)
    st.subheader('2. 基础过滤（手工选择）')
    c1,c2,c3,c4=st.columns(4)
    with c1: sum_min=st.slider('和值下限',0,45,0)
    with c2: sum_max=st.slider('和值上限',0,45,45)
    with c3: span_min=st.slider('跨度下限',0,9,0)
    with c4: span_max=st.slider('跨度上限',0,9,9)
    if sum_min>sum_max or span_min>span_max:
        st.error('基础过滤区间上下限不能颠倒')
        return
    baseline=[BasicConstraint('sum', sum_min,sum_max),BasicConstraint('span',span_min,span_max)]
    if st.button('运行历史规则识别及候选过滤',type='primary'):
        try:
            with st.spinner('计算全部10万个号码的指标和模式...'):
                result=filter_next(history,config)
                combined=combine_basic_and_pattern(baseline, result.kept)
                st.session_state['pattern_analysis']={
                    'summary':result.summary(),'rules':[x.as_dict() for x in result.rules],
                    'combined':combined,'config':config,'history':history}
        except Exception as e: st.error(str(e))
    saved=st.session_state.get('pattern_analysis')
    if saved and saved['config']==config and saved['history']==history:
        st.subheader('3. 过滤结果')
        s=saved['summary'];combined=saved['combined']
        a,b,c=st.columns(3)
        a.metric('历史模式规则剔除',f'{s["removed_rate"]:.2%}')
        b.metric('基础与历史规则叠加后保留',f'{len(combined):,} 注')
        c.metric('公平随机数学基线覆盖率',f'{len(combined)/100000:.2%}')
        df=pd.DataFrame(saved['rules'])
        if not df.empty:
            st.dataframe(df[['label','window','observed','banned_values','raw_removed','removed_after_previous','status','reason']],hide_index=True,use_container_width=True)
        kept='number\n'+'\n'.join(f'{int(i):05d}' for i in combined)+'\n'
        st.download_button('导出候选号码CSV', kept.encode('utf-8-sig'), 'pl5_候选号码.csv', 'text/csv')
        st.download_button('导出规则及结果JSON', json.dumps({k:v for k,v in saved.items() if k in ('summary','rules')},ensure_ascii=False,indent=2).encode(),
                           'pl5_规则报告.json','application/json')
    st.subheader('4. 前向滚动回测（模式过滤）')
    periods=st.number_input('验证多少期（仅使用每期之前的数据）',5,200,30)
    if st.button('运行滚动回测'):
        if len(history)<max(30,max(wins))+5:
            st.error('历史期数不足')
        else:
            with st.spinner('逐期构造规则和候选集，不使用未来数据...'):
                report=rolling_backtest(history,config,warmup=max(30,max(wins)),max_periods=int(periods))
            a,b=st.columns(2)
            a.metric('实际保留开奖号的期数',f'{report["observed_keep"]}/{report["periods"]}')
            b.metric('相同规模随机基线预期保留期数',f'{report["random_expected_keep"]:.2f}')
            st.info(report['note'])
            st.dataframe(pd.DataFrame(report['details']),use_container_width=True,hide_index=True)
            st.download_button('导出回测报告',json.dumps(report,ensure_ascii=False,indent=2).encode(),'pl5_回测报告.json','application/json')

if __name__=='__main__': render()
