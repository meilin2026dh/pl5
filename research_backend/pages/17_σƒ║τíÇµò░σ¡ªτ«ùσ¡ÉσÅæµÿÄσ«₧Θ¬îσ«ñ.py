"""PL5 V2.9 autonomous finite-domain elementary binary operation laboratory."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import streamlit as st
from pailie5.primitive_invention_v29 import study, history_array, discover
from research_v24 import read_history

st.set_page_config(page_title='PL5 · 基础数学算子发明实验室',layout='wide')
st.title('PL5 V2.9 · 基础数学算子发明实验室')
st.caption('从10×10的数学运算真值表开始发明新算子；开发验证、封存测试、科学证伪。研究用途，不是中奖概率承诺。')
st.warning('系统生成的自定义二元运算是数据诱导的有限运算表，不是新数学定理；合成数据不能作为官方开奖预测成绩。')

mode=st.radio('研究数据', ['独立均匀演示','人工关联演示','上传已核验的官方开奖CSV'],horizontal=True)
file=st.file_uploader('CSV需含number列，建议issue,date,number',type='csv') if mode.startswith('上传') else None
c1,c2,c3=st.columns(3)
with c1: maximum=st.slider('每轮最多新算子',1,40,20)
with c2: budget=st.slider('最终研究候选注数',1,100,100)
with c3: seed=st.number_input('研究种子',min_value=0,max_value=4294967295,value=20261102,step=1)
c4,c5=st.columns(2)
with c4: val=st.slider('开发验证期数',40,120,60)
with c5: hold=st.slider('最后封存期数',30,120,50)

if st.button('自主发明并独立验证',type='primary',use_container_width=True):
    try:
        if mode.startswith('上传'):
            if file is None:st.error('请先上传经过核验的历史CSV');st.stop()
            raw=file.getvalue().decode('utf-8-sig')
            # Strict validation from the shared input parser.
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'official.csv';path.write_text(raw,encoding='utf-8-sig')
                history=read_history(path)
            source='用户上传的CSV（真实官方来源未独立核验）'
        else:
            rng=np.random.default_rng(int(seed))
            matrix=rng.integers(0,10,(800 if '人工关联' in mode else 500,5))
            if '人工关联' in mode:matrix[:,1]=matrix[:,0]
            history=[''.join(str(x) for x in row) for row in matrix]
            source='合成数据：'+mode
        result=study(history,seed=int(seed),maximum=maximum,budget=budget,
                     validation_periods=val,holdout_periods=hold)
        result['source']=source
        st.session_state['v29_result']=result
    except Exception as error:
        st.error(f'研究失败：{error}')

r=st.session_state.get('v29_result')
if r:
    a,b,c,d=st.columns(4)
    a.metric('新算子数量',r['new_unique_primitives'])
    b.metric('验证的模型方案',r['tests_counted'])
    c.metric('样本外证据门禁','通过' if r['validation_gate']['passed'] else '拒绝，均匀回退')
    d.metric('研究候选集',len(r['experimental_top_k']))
    st.caption('门槛为严格限定的公平独立零假设下终端e-value并集控制；无法说明实际设备是否公平。')
    st.subheader('自主发明的基础运算')
    frame=pd.DataFrame([{'能力ID':c['id'],'位置':','.join(map(str,c['positions'])),
            '生成机制':c['family'],'类别数':c['properties']['occupied_output_classes'],
            '历史分区稳定性':round(c['properties']['partition_stability_train_halves'],3),
            '信息熵(bit)':round(c['properties']['partition_entropy_bits'],3)} for c in r['cards']])
    st.dataframe(frame,use_container_width=True,hide_index=True)
    if r['cards']:
        ids=[c['id'] for c in r['cards']]
        selected=st.selectbox('查看自定义二元运算的100格真值表',ids)
        card=next(c for c in r['cards'] if c['id']==selected)
        t=np.array(card['table']).reshape(10,10)
        st.dataframe(pd.DataFrame(t,index=[f'a={i}' for i in range(10)],columns=[f'b={i}' for i in range(10)]),use_container_width=True)
        st.json({k:v for k,v in card.items() if k!='table'})
    st.subheader('实验结果与证据')
    st.json({'selected_operator':r['selected_operator'],'validation_gate':r['validation_gate'],
        'sealed_holdout':r['sealed_holdout'],'crosscheck':r['independent_full_universe_crosscheck']})
    st.text('研究候选（前30个）：'+', '.join(r['experimental_top_k'][:30]))
    st.download_button('下载实验报告JSON',json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),
                       file_name='pl5_v29_primitive_research.json',mime='application/json')
    csvtxt='number,group\n'+''.join(f'{x},research_top_k\n' for x in r['experimental_top_k'])+''.join(f'{x},random_control\n' for x in r['equal_budget_random_control'])
    st.download_button('下载候选与随机对照CSV',csvtxt,file_name='pl5_v29_research_candidates.csv',mime='text/csv')
    st.caption('用户需要用经过核验的官方历史资料运行前向实验，并明确开奖前时间封存；不能直接把研究分数当中奖概率。')
