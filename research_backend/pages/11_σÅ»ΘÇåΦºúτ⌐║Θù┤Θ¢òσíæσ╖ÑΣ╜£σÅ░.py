"""PL5 V1.1 reversible ESSE workbench. Nothing runs autonomously on page open."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pailie5.data import load_csv
from pailie5.pattern_rules import Configuration, PATTERN_CN, indicator_table, EXTRA_INDICATORS
from pailie5.space_mapping import register_space_indicators
from pailie5.sculpting import SculptSession, knives_from_history, rolling_sculpt_backtest
from pailie5.basic_filters import BasicConstraint

st.set_page_config(page_title='PL5 V1.1 · 可逆解空间雕塑',layout='wide')
st.title('PL5 V1.1 · 自进化解空间雕塑实验台')
st.warning('本页展示的是可撤销的过滤策略与未校准偏好排名。公平独立开奖时100注的命中概率仍为0.1%，10期至少一次约0.996%。')
st.caption('先导入历史 → 自动发现指标模式 → 选择雕刻刀 → 逐刀审计 → 撤销/保护/排序 → 输出100注及完整10万注。')
root=Path(__file__).resolve().parents[1]
with st.sidebar:
    st.header('① 数据与过滤参数')
    uploaded=st.file_uploader('导入官方核验的CSV（period,number）',type=['csv'],key='esse_file')
    demo=st.checkbox('使用合成演示数据',value=uploaded is None)
    register_space_indicators()
    possible=list(indicator_table())+list(EXTRA_INDICATORS)
    preset=['sum','span','odd_count','digit_1','digit_5']
    indicators=st.multiselect('指标（含跨空间映射）',possible,default=preset)
    windows=st.multiselect('观察历史窗口',list(range(3,13)),default=[3,4])
    patterns=st.multiselect('反延续模式',list(PATTERN_CN),default=['constant','strict_up','arithmetic'])
    transforms=st.multiselect('指标转换',['raw','mod2','mod3','mod5','mod10'],default=['raw'])
    max_rules=st.slider('本轮最多使用的规则',5,100,30)
    manual_sum=st.checkbox('添加基础和值上限规则',False)
    sum_limit=st.slider('和值最大允许值',0,45,32,disabled=not manual_sum)
    k=st.number_input('目标候选数量',min_value=1,max_value=100_000,value=100,step=10)
    weight_strength=st.slider('偏好评分强度（不影响硬过滤）',0.0,8.0,1.0,0.25)
    strict=st.checkbox('证据约束模式（无外部审批则所有刀具禁止启用）',False)

if not demo and uploaded is None:
    st.info('请上传经官方公告核验的开奖记录，或勾选演示模式。')
    st.stop()
if not (indicators and windows and patterns and transforms):
    st.info('请选择至少一项指标、一种窗口、模式和变换。')
    st.stop()
try:
    data=(root/'data'/'synthetic_demo.csv').read_bytes() if demo else uploaded.getvalue()
    dataset=load_csv(data,is_demo=demo)
    hist=dataset.frame['number'].tolist()
    cfg=Configuration(indicators=tuple(indicators),windows=tuple(sorted(windows)),
        patterns=tuple(patterns),transforms=tuple(transforms),max_rules=int(max_rules),
        max_total_remove=.99,min_keep=100)
    basic=[BasicConstraint('sum',maximum=int(sum_limit))] if manual_sum else []
    identity=hashlib.sha256(data+repr((cfg,basic,strict)).encode()).hexdigest()
    if st.session_state.get('esse_id') != identity:
        knives, defaults=knives_from_history(hist,cfg,basic,max_knives=max_rules)
        st.session_state['esse_session']=SculptSession(knives,enabled=defaults,
                 mode='strict' if strict else 'explore')
        st.session_state['esse_id']=identity
    session: SculptSession=st.session_state['esse_session']
except Exception as exc:
    st.error(f'构建规则失败：{exc}')
    st.stop()

st.caption(f'数据：{len(hist)}期；演示模式={demo}；发现候选雕刻刀={len(session.knives)}；当前已请求启用={len(session.enabled_keys)}。')
for w in dataset.warnings: st.caption(w)

st.subheader('② 选择与操作雕刻刀')
keys=list(session.order)
labels={key:f'{i+1}. {session.knives[key].label} | {key[-8:]}' for i,key in enumerate(keys)}
with st.form('esse_selection'):
    selected=st.multiselect('本轮希望启用的规则（可选被旧版护栏跳过的规则）',keys,
                 default=list(session.enabled_keys),format_func=lambda x:labels[x])
    clicked=st.form_submit_button('应用规则选择')
if clicked:
    session.set_selected(selected)
    st.rerun()

c1,c2,c3=st.columns(3)
with c1:
    if st.button('撤销上一次操作'):
        session.undo();st.rerun()
with c2:
    if st.button('重做'):
        session.redo();st.rerun()
with c3:
    if st.button('建议按新增排除数量排列（不改善概率）'):
        session.set_order(session.suggest_greedy_order());st.rerun()

x1,x2,x3=st.columns(3)
with x1:
    picked=st.selectbox('选中一把刀以调整优先顺序及权重',keys,
                 format_func=lambda x:labels[x]) if keys else None
with x2:
    if st.button('将选中刀上移',disabled=picked is None):
        session.move(picked,-1);st.rerun()
with x3:
    if st.button('将选中刀下移',disabled=picked is None):
        session.move(picked,+1);st.rerun()
if picked:
    with st.form('weight_form'):
        new_weight=st.slider('选中刀的偏好权重',0.0,10.0,float(session.weight_of(picked)),0.25)
        if st.form_submit_button('保存权重（可撤销）'):
            session.set_weight(picked,new_weight);st.rerun()
with st.form('protect_form'):
    p1,p2,p3=st.columns([2,1,1])
    with p1: number=st.text_input('手动恢复或取消保护号码（严格五位）',value='00128')
    with p2: protect=st.radio('操作',['恢复/保护','取消保护'],horizontal=False)
    with p3: sent=st.form_submit_button('执行号码操作')
    if sent:
        try:
            session.protect(number,protect=='恢复/保护');st.rerun()
        except ValueError as e: st.error(str(e))

sculpt=session.sculpt()
audit=sculpt.audit
st.subheader('③ 逐刀压缩与可逆性审计')
m1,m2,m3,m4=st.columns(4)
m1.metric('严格保留',f'{audit["kept"]:,}')
m2.metric('实际过滤',f'{audit["removed"]:,}')
m3.metric('理论随机覆盖率',f'{audit["fair_random_coverage"]:.3%}')
m4.metric('未通过审批的阻断刀具',audit['unapproved_blocked'])
if strict:
    st.info('当前为证据约束模式：系统未提供外部审计签名授权，默认阻断所有尚未验证的规则；不根据自填的“已验证”标签放行。')
if sculpt.stages:
    stages=pd.DataFrame([s.as_dict() for s in sculpt.stages])
    st.dataframe(stages.rename(columns={'step':'序号','key':'规则键','label':'规则',
          'before':'过滤前','after':'过滤后','newly_removed':'本刀新增排除',
          'already_removed':'已被其他前序刀排除','raw_removed':'单刀原始排除',
          'unique_recoverable':'撤销此刀独立可恢复','fair_coverage_after':'随机覆盖率'}),
          hide_index=True,use_container_width=True)
    st.line_chart(stages.set_index('step')['after'],x_label='刀具序号',y_label='剩余注数')
    st.subheader('④ 刀具的实际边际贡献（不受执行顺序影响）')
    st.dataframe(pd.DataFrame(session.counterfactual()),hide_index=True,use_container_width=True)
else:
    st.info('当前没有启用的雕刻刀。10万注仍在全空间中，默认使用固定种子破除相同分数的并列。')

st.subheader('⑤ 全10万注可逆评分与100注名单')
with st.spinner('对全10万注重算评分、保留与恢复标记…'):
    ranked,summary=session.rank(k=int(k),strength=weight_strength)
st.caption('如果各刀将候选压缩至不足目标K注，系统会从被排除号码中按规则惩罚最小原则补回，报告中逐个标记。该评分没有经过真实中奖概率校准。')
c1,c2,c3=st.columns(3)
c1.metric('最终候选数',summary['selected'])
c2.metric('因不足K补回',summary['restored_for_quota'])
c3.metric('公平开奖下10期至少一中',f'{summary["fair_10_draw_at_least_one"]:.4%}')
st.dataframe(ranked.head(int(k)),hide_index=True,use_container_width=True)
st.download_button('下载本期K注名单CSV',ranked.head(int(k)).to_csv(index=False).encode('utf-8-sig'),
                   file_name='PL5_V11_本期候选.csv',mime='text/csv')
st.download_button('下载10万注评分CSV',ranked.to_csv(index=False).encode('utf-8-sig'),
                   file_name='PL5_V11_全号码雕塑审计.csv',mime='text/csv')
st.download_button('下载审计报告JSON',json.dumps({'summary':summary,
               'stages':[x.as_dict() for x in sculpt.stages],
               'counterfactual':session.counterfactual(),
               'history_hash':hashlib.sha256(data).hexdigest()},
               indent=2,ensure_ascii=False).encode('utf-8'),
               file_name='PL5_V11_可逆雕塑审计.json',mime='application/json')

st.divider()
st.subheader('⑥ 逐期滚动探索回测')
st.caption('所有候选规则用对应待测期之前的数据重建；这是可重复调参的探索性回测，并非独立封存或前瞻验收。')
roll_count=st.slider('仅检验最近多少期',3,30,6)
if st.button('开展探索性逐期回测'):
    with st.spinner('逐期重建刀具并输出前K名，可能需要一些计算时间…'):
        try:
            result=rolling_sculpt_backtest(hist,cfg,k=int(k),warmup=max(40,max(windows)),
                         max_periods=roll_count,basic=basic)
            st.session_state['esse_bt']=(identity,int(k),result)
        except Exception as exc: st.error(str(exc))
old=st.session_state.get('esse_bt')
if old and old[0]==identity and old[1]==int(k):
    bt=old[2]
    st.write(f'观测命中 {bt["hits"]} / {bt["periods"]}；随机基线期望 {bt["fair_expected_hits"]:.4f} 次。')
    st.dataframe(pd.DataFrame(bt['details']),hide_index=True,use_container_width=True)
    st.info(bt['note'])
    st.download_button('下载滚动回测JSON',json.dumps(bt,indent=2,ensure_ascii=False).encode('utf-8'),
                       file_name='PL5_V11_逐期回测.json')
