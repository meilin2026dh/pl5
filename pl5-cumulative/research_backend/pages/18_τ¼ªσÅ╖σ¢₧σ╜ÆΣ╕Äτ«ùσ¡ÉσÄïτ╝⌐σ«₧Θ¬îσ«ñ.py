"""V3.0: research-only symbolic compression of learned mathematical primitives."""
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import streamlit as st
from pailie5.symbolic_operators_v30 import search_formula, structural_summary, analyze_primitives
from research_v24 import read_history

st.set_page_config(page_title='PL5 V3.0 · 符号数学发现实验室', layout='wide')
st.title('PL5 V3.0 · 开放式符号回归与算子压缩')
st.caption('研究路径：有限域基础算子→表达式搜索→100格重建证书→稀疏数学关系报告→AAN科研登记。')
st.warning('这是一种有界语法上的数学表达发现，而非无限制发明新公理。数学可压缩性不等于彩票开奖号码可预测。')
mode = st.radio('研究场景',['已知数学公式正确性验证','合成开奖自主发现','上传经核验的官方开奖CSV'],horizontal=True)
a,b,c=st.columns(3)
with a: width=st.slider('候选搜索束宽',4,60,24)
with b: nodes=st.select_slider('最大表达式节点数',options=[3,5,7],value=5)
with c: seed=st.number_input('确定性研究种子',0,2**32-1,20261102)
maximum=st.slider('合成或官方历史研究算子数',1,20,5)
upload=st.file_uploader('使用官方开奖前，请核验CSV来源与期号；需要number列',type=['csv']) if '上传' in mode else None

if st.button('运行数学发现与100格等价性检验',type='primary',use_container_width=True):
    try:
        if mode.startswith('已知'):
            x,y=np.indices((10,10));truth=(x+y)%3
            cert=search_formula(truth,seed=int(seed),beam_width=width,max_nodes=nodes)
            outcome={'source':'明确已知数学公式（功能夹具）',
                     'items':[{'operator_id':'known-add-mod3','symbolic':cert.as_card(),
                               'table_structure':structural_summary(truth)}],
                     'generated':1}
        else:
            if mode.startswith('上传'):
                if upload is None:raise ValueError('请先上传CSV')
                raw=upload.getvalue().decode('utf-8-sig')
                with tempfile.TemporaryDirectory() as d:
                    p=Path(d)/'history.csv';p.write_text(raw,encoding='utf-8-sig')
                    hist=read_history(p)
                source='用户上传CSV（本页面未核实官方来源）'
            else:
                rng=np.random.default_rng(int(seed))
                sample=rng.integers(0,10,(300,5))
                hist=[''.join(map(str,row)) for row in sample]
                source='独立均匀合成数据'
            outcome=analyze_primitives(hist,seed=int(seed),maximum=maximum,beam_width=width,max_nodes=nodes)
            outcome['source']=source
        st.session_state['v30_symbolic']=outcome
    except Exception as exc:
        st.error(f'实验终止：{exc}')

report=st.session_state.get('v30_symbolic')
if report:
    items=report['items']
    c1,c2,c3=st.columns(3)
    c1.metric('研究算子',len(items))
    c2.metric('完全等价的简洁公式',sum(x['symbolic']['status']=='exact_symbolic' for x in items))
    c3.metric('正确保留原运算表',sum(x['symbolic']['status']=='raw_table_preferred' for x in items))
    data=[]
    for row in items:
        s=row['symbolic']
        data.append({'算子ID':row['operator_id'],'结果状态':s['status'],
                     '找到的表达式':s['formula'] or '无','100格误差':s['whole_table_errors'],
                     '陌生输入对误差':s['unseen_pair_errors'],
                     '表示位数/原表位数':round(s['compression_ratio'],3) if s['compression_ratio'] else None})
    st.dataframe(pd.DataFrame(data),use_container_width=True,hide_index=True)
    if items:
        choice=st.selectbox('查看能力说明书与数学结构',[x['operator_id'] for x in items])
        selected=next(x for x in items if x['operator_id']==choice)
        st.json(selected)
    st.download_button('下载完整科研报告JSON',json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),
                       file_name='PL5_V30_symbolic_research.json',mime='application/json')
    st.caption('100格数学恒等核验只验证算子表达式，不是历史开奖的前向预测；无数学结构的真值表应保留完整查表实现。')
