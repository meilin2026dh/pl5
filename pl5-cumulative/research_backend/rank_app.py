"""PL5 相对概率排序研究台：streamlit run rank_app.py"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pailie5.space_mapping import register_space_indicators
from pailie5.pattern_rules import EXTRA_INDICATORS
SPACE_INDICATOR_LABELS = register_space_indicators()
from pailie5.data import load_csv
from pailie5.pattern_rules import (
    Configuration, PATTERN_CN, filter_next, historical_indicators,
    indicator_table, CONTEXT_INDICATORS,
)
from pailie5.probability_ranker import rule_key, rank_all_numbers, rolling_rank_backtest
from pailie5.basic_filters import BasicConstraint


INDICATOR_CN = {**SPACE_INDICATOR_LABELS, 
    'sum':'和值','span':'跨度','odd_count':'奇数个数','high_count':'大数个数',
    'unique_count':'不同数字数','adjacent_equal':'邻位相同对数',
    'adjacent_up':'邻位递增次数','adjacent_down':'邻位递减次数',
    'adjacent_consecutive':'邻位相差1次数','max_frequency':'同一数字最多出现次数',
    'first_last_gap':'首尾差','head_sum':'前两位和值','tail_sum':'后两位和值',
    'middle_sum':'中三位和值','even_position_sum':'偶数位置和值',
    'odd_position_sum':'奇数位置和值','mirror_pairs':'对称位置相同对数',
    'inner_span':'内三位跨度','same_positions_prev':'与上期同位置重合数',
    'same_parity_positions_prev':'与上期同位置奇偶一致数',
    'digit_overlap_prev':'与上期相同数字的重合数',
    'sum_delta_prev':'和值较上期变化','span_delta_prev':'跨度较上期变化',
    'lastdigit_delta_prev':'末位较上期变化',
    **{f'digit_{i}':f'第{i}位数字' for i in range(1,6)},
}


def render():
    st.set_page_config(page_title='PL5 | 十万号码排序', layout='wide')
    st.title('PL5 · 时序反延续与十万号码排序')
    st.caption('V0.3 · 历史指标选择 → 规则检测 → 人工启用 → 相对评分 → 全量排名 → 逐期回测')
    st.warning('重要：公平独立开奖条件下，每个5位号码的真实下一期概率始终是0.001%。下方“模型概率”是由用户选择的启发式惩罚经Softmax归一化生成的研究权重，尚未校准，也没有证据表明能提高中奖概率。')

    uploaded = st.file_uploader('上传已核对官方公告的历史开奖 CSV（period,number）', type=['csv'], key='rank_csv')
    demo = st.checkbox('使用合成数据体验界面（非官方开奖）', value=uploaded is None)
    if not demo and uploaded is None:
        st.info('请上传官方核对过的CSV，或选择合成演示数据。')
        return
    try:
        raw = ((Path(__file__).parent / 'data' / 'synthetic_demo.csv').read_bytes()
               if demo else uploaded.getvalue())
        loaded = load_csv(raw, is_demo=demo)
        hist = loaded.frame['number'].tolist()
        history_key = (len(hist), tuple(hist[-20:]))
        st.caption(f'已读取 {len(hist)} 期；最近期号 {loaded.frame.iloc[-1]["period"]}' + ('；合成示例数据' if demo else '；由用户声明为官方核验数据'))
        for note in loaded.warnings: st.caption(note)
    except Exception as exc:
        st.error(f'CSV格式错误：{exc}')
        return

    available = tuple(indicator_table()) + tuple(CONTEXT_INDICATORS) + tuple(EXTRA_INDICATORS)
    with st.sidebar:
        st.subheader('① 选指标和窗口')
        inds = st.multiselect('计算哪些指标', available,
              default=['sum','span','odd_count','digit_5','same_positions_prev'],
              format_func=lambda v: f'{INDICATOR_CN.get(v,v)}（{v}）')
        trans = st.multiselect('指标变换', ['raw','mod2','mod3','mod5','mod10'],default=['raw'])
        patterns = st.multiselect('自动检测哪些模式', list(PATTERN_CN),
                    default=['constant','strict_up','strict_down','arithmetic','period2','zigzag'],
                    format_func=lambda p: PATTERN_CN[p])
        windows = st.multiselect('查看最近几期（窗口）', list(range(3,13)), default=[3,4,6])
        mode = st.radio('规则发现逻辑', ['continuation','recurrence'],
                        format_func=lambda v: '最近N期规律继续延长' if v=='continuation' else '近段内有该类规律，检测其重新形成')
        lookback=st.slider('近期搜索范围（期）',6,60,15)
        st.divider()
        st.subheader('② 排序设置')
        strength=st.slider('反延续偏好强度（仅影响启发式权重）',0.0,4.0,1.0,0.25)
        top_k=st.select_slider('关注排名前K注',options=[100,200,500,1000,2000,5000,10000,20000],value=1000)
        st.subheader('③ 基础规则')
        basic_enabled=st.checkbox('标记基础区间过滤是否通过',value=False)
        sum_bounds=st.slider('和值允许区间',0,45,(0,45)) if basic_enabled else (0,45)
        span_bounds=st.slider('跨度允许区间',0,9,(0,9)) if basic_enabled else (0,9)

    if not inds or not trans or not patterns or not windows:
        st.info('需要至少一个指标、变换、模式和窗口。')
        return
    cfg=Configuration(indicators=tuple(inds),transforms=tuple(trans),patterns=tuple(patterns),
                      windows=tuple(sorted(windows)),mode=mode,lookback=max(lookback,max(windows)))
    st.subheader('1 · 最近几期指标')
    recent=historical_indicators(hist,tuple(inds))[-max(windows)-3:]
    st.dataframe(pd.DataFrame(recent).rename(columns=INDICATOR_CN),hide_index=True,use_container_width=True)

    if st.button('识别当前可用模式',type='primary'):
        with st.spinner('对各指标的历史窗口检测模式…'):
            detection=filter_next(hist,cfg)
            options=[]
            for r in detection.rules:
                options.append({'key':rule_key(r),'name':(
                    f'{INDICATOR_CN.get(r.indicator,r.indicator)} / {r.transform} / {PATTERN_CN[r.pattern]} '
                    f'/ 窗口{r.window}期 / 历史{r.observed} / 待避开值{r.banned_values} '
                    f'/ 覆盖{r.raw_removed_rate:.1%} / {r.status}'),
                    'default':r.status=='applied'})
            st.session_state['rank_detection'] = {'cfg':cfg,'history_key':history_key,'options':options,
                'data':detection.summary(), 'rules':[r.as_dict() for r in detection.rules]}
            # 新的探测结果默认启用已被硬过滤引擎接受的规则，用户可改。
            st.session_state['rank_selected']=[x['key'] for x in options if x['default']]
            st.session_state.pop('rank_result',None)

    detection=st.session_state.get('rank_detection')
    if not detection or detection['cfg'] != cfg or detection['history_key'] != history_key:
        st.info('先点击“识别当前可用模式”，再自行选择哪些规则用于本期排序。')
        return
    st.subheader('2 · 用户自主选择规则')
    option_map={x['key']:x['name'] for x in detection['options']}
    if not option_map:
        st.info('该窗口未检测到匹配模式。可以调整指标/窗口，或输出全部同分的公平基线。')
        selected=[]
    else:
        selected=st.multiselect('勾选参与本期评分的规则（包括因硬删除上限被跳过的规则）',
                  list(option_map),format_func=lambda x:option_map[x],key='rank_selected')
    st.caption(f'检测规则：{len(option_map)} 条；用户启用：{len(selected)} 条。规则覆盖率并不等于“预测会失效的概率”。')

    basic = ([BasicConstraint('sum',minimum=sum_bounds[0],maximum=sum_bounds[1]),
              BasicConstraint('span',minimum=span_bounds[0],maximum=span_bounds[1])]
             if basic_enabled else [])
    params=(cfg,history_key,tuple(sorted(selected)),strength,tuple(sum_bounds),tuple(span_bounds),basic_enabled)
    if st.button('对10万个号码计算相对权重与排名'):
        with st.spinner('全号码枚举并归一化模型权重...'):
            try:
                result=rank_all_numbers(hist,cfg,strength=strength,selected_rule_keys=selected,
                                        basic_constraints=basic)
                st.session_state['rank_result']={'params':params,'output':result}
            except Exception as exc:
                st.error(str(exc))
    result_wrapper=st.session_state.get('rank_result')
    if result_wrapper and result_wrapper['params']==params:
        output=result_wrapper['output']
        st.subheader('3 · 全量排名（可下载10万注）')
        summ=output.summary(top_k=top_k)
        c1,c2,c3,c4=st.columns(4)
        c1.metric('本轮启用规则',summ['selected_rule_count'])
        c2.metric('公平基线每注概率','0.001%')
        c3.metric(f'前{top_k:,}注公平覆盖概率',f'{summ["fair_top_k_coverage"]:.2%}')
        c4.metric(f'前{top_k:,}注模型权重总和',f'{summ["model_assigned_top_k_mass"]:.2%}')
        st.caption('第四项为未校准启发式模型的主观权重，不是实际命中率；不得与公平基线混淆。相同评分号码按号码顺序排列，组内没有预测区分能力。')
        st.dataframe(output.table.head(min(top_k,3000)),hide_index=True,use_container_width=True)
        st.download_button('下载全部100,000注排名CSV',
            output.table.to_csv(index=False).encode('utf-8-sig'),'pl5_十万号码排名_研究权重.csv','text/csv')
        st.download_button('下载规则详情与概率说明JSON',
            json.dumps({'summary':summ,'rule_details':output.rule_details},ensure_ascii=False,indent=2).encode('utf-8'),
            'pl5_概率排序说明.json','application/json')

    st.subheader('4 · 独立于当前人工勾选的滚动排名回测')
    st.caption('采用每期自动批准的模式规则进行历史模拟；如需检验本期人工挑选策略，必须提前明确一套可复现的“挑选规则”才可做公平回测。')
    periods=st.number_input('回测最近多少期',min_value=3,max_value=100,value=10,step=1)
    if st.button('执行滚动排名回测'):
        try:
            with st.spinner('每一步只使用待测期之前的数据，逐期排名...'):
                report=rolling_rank_backtest(hist,cfg,warmup=max(30,max(windows)),
                    max_periods=int(periods),top_k=top_k,strength=strength)
            a,b,c=st.columns(3)
            a.metric('实际进入前K的期数',f'{report["top_k_hits"]} / {report["periods"]}')
            b.metric('相同K随机期望命中期数',f'{report["fair_expected_top_k_hits"]:.3f}')
            c.metric('相对均匀基线的平均对数损失改善',f'{report["log_loss_improvement_vs_fair"]:+.5f}')
            st.info(report['note'])
            st.dataframe(pd.DataFrame(report['details']),hide_index=True,use_container_width=True)
            st.download_button('下载排名回测报告',json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'),
                               'pl5_排名滚动回测.json','application/json')
        except Exception as exc:
            st.error(f'回测失败：{exc}')


if __name__=='__main__': render()
