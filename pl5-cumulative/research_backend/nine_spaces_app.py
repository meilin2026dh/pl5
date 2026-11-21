"""Standalone research UI; launch with uv run streamlit run nine_spaces_app.py."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st
from pailie5.nine_spaces_v24 import Spaces,Rule,compose,capability_cards,predefined_exploratory_rules,FAMILIES,walk_forward
from research_v24 import read_history
from pathlib import Path

st.set_page_config(page_title='PL5 多空间实验室 V2.4',layout='wide')
st.title('PL5 · 九空间特征与协同雕塑实验室')
st.warning('实验性形态过滤≠预测优势。公平独立开奖时，每期100注的精确命中率基线为0.1%。')
with st.sidebar:
    st.header('研究设置')
    uploaded=st.file_uploader('导入已核验的开奖CSV',type=['csv'])
    use_demo=st.checkbox('使用合成演示开奖',value=uploaded is None)
    window=st.number_input('历史窗口期数',min_value=3,max_value=10000,value=100)
    family=st.selectbox('选择研究空间',list(FAMILIES)[:-1],format_func=lambda x:FAMILIES[x])
    budget=st.number_input('最终候选号码数量',1,100000,100)
    seed=st.number_input('随机种子',0,2**31-1,42)

if uploaded is not None and not use_demo:
    import csv,io
    rows=list(csv.DictReader(io.StringIO(uploaded.getvalue().decode('utf-8-sig'))))
    if rows and 'date' in rows[0]:rows.sort(key=lambda r:r['date'])
    elif rows and 'period' in rows[0]:rows.sort(key=lambda r:r['period'])
    elif rows and 'issue' in rows[0]:rows.sort(key=lambda r:r['issue'])
    history=[r['number'] for r in rows]
else:
    history=[f'{(i*7919+i*i*17)%100000:05d}' for i in range(160)]
    st.info('当前使用合成演示数据，不是中国体育彩票官方数据。')
history=history[-int(window):]
try:
    engine=Spaces(history)
    metric_options=list(engine.get(family))
except Exception as e:
    st.error(f'无法计算该空间指标：{e}')
    st.stop()
metric=st.selectbox('选择指标',metric_options)
operator=st.selectbox('设置规则条件',['eq','ne','ge','gt','le','lt','between','in','not_in'],
                      format_func=lambda x:{'eq':'等于','ne':'不等于','ge':'≥','gt':'>','le':'≤','lt':'<','between':'区间内','in':'集合内','not_in':'集合外'}[x])
value_str=st.text_input('阈值（JSON数字或数字数组）','0')
action=st.radio('条件语义',['exclude','retain'],format_func=lambda x:'符合则过滤' if x=='exclude' else '符合才保留',horizontal=True)
tab1,tab2,tab3=st.tabs(['单空间指标','九空间联合雕塑','算法能力说明书'])
with tab1:
    values=engine.get(family)[metric]
    st.write('该指标在整个100,000号码空间上的取值范围与分布：')
    series=pd.Series(values)
    st.metric('不同指标取值',len(series.unique()))
    st.dataframe(series.value_counts().sort_index().rename_axis('指标取值').reset_index(name='号码数').head(500),hide_index=True)
    if len(history):
        df=pd.DataFrame({'历史序号':range(max(0,len(history)-10),len(history)),
                         '号码':history[-10:],
                         '指标值':[values[int(x)] for x in history[-10:]]})
        st.write('最近10期指标值（由所选择历史窗口计算）：')
        st.dataframe(df,hide_index=True)
with tab2:
    st.write('规则不会自动开启；可选单一指标，也可选预设五层交集进行审计。')
    use_five=st.checkbox('测试五条预设跨空间实验规则',value=False)
    try:
        value=json.loads(value_str)
        rules=predefined_exploratory_rules() if use_five else [Rule('manual',family,metric,operator,value,action)]
        if st.button('运行规则、审计重叠并输出候选',type='primary'):
            out=compose(history,rules,budget=int(budget),seed=int(seed))
            st.session_state['nine_spaces_v24_result']=out
        out=st.session_state.get('nine_spaces_v24_result')
        if out:
            a,b,c=st.columns(3)
            a.metric('严格过滤后剩余',out['strict_remaining'])
            b.metric('研究性Top-K',len(out['ranked_numbers']))
            c.metric('公平随机Top-K覆盖率',f"{out['ranked_exact_random_coverage']*100:.4f}%")
            st.dataframe(pd.DataFrame(out['audit']),hide_index=True)
            st.dataframe(pd.DataFrame(out['overlaps']),hide_index=True)
            st.download_button('下载研究报告(JSON)',json.dumps(out,ensure_ascii=False,indent=2).encode(),
                               'PL5_V24_多空间实验报告.json',mime='application/json')
            st.download_button('下载候选号码(CSV)',pd.DataFrame({'number':out['ranked_numbers']}).to_csv(index=False).encode('utf-8-sig'),
                               'PL5_V24_研究候选.csv',mime='text/csv')
    except Exception as e:
        st.error(str(e))
with tab3:
    st.dataframe(pd.DataFrame(capability_cards()),hide_index=True)
    st.caption('能力已提供输入输出与版本描述；目前不会通过该界面自动发布到正式算法准入库。')
