"""PL5 V3.2 operator-category lab, never enables live filters."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st
from pailie5.category_hypotheses_v32 import infer_new_categories, synthetic_fixtures, study_historical_operators
from pailie5.primitive_categories_v31 import run_operator_on_100k
from research_v24 import read_history

st.set_page_config(page_title='PL5 V3.2 数学类别自进化',layout='wide')
st.title('PL5 V3.2 · 自主数学类别假设实验室')
st.caption('自动提出数学类别候选→完整100格证明→与V3.1描述长度对照→AAN能力卡与ESSE研究掩码')
st.warning('所有能力均为research_only。数学压缩不证明彩票可预测，界面不会自动启用过滤或购买。')
mode=st.radio('研究数据',['合成对照表','上传运算表JSON','历史CSV研究'],horizontal=True)
file=st.file_uploader('上传10×10数学表或历史CSV',type=['json'] if mode=='上传运算表JSON' else ['csv']) if mode!='合成对照表' else None
max_exceptions=st.slider('允许的稀疏例外点上限',0,6,5)
min_saved=st.slider('至少优于V3.1的位数',1,80,1)
maximum=st.slider('历史研究最多探索的V2.9原始运算表',1,20,6)
if st.button('运行类别假设发明与审查',type='primary',use_container_width=True):
    try:
        if mode=='合成对照表':
            tables=synthetic_fixtures()
        elif mode=='上传运算表JSON':
            if file is None:raise ValueError('请先上传数学表')
            if file.size>1024*1024:raise ValueError('JSON文件超过1MiB')
            tables={'用户数学表':np.asarray(json.loads(file.getvalue().decode('utf-8-sig')))}
        else:
            if file is None:raise ValueError('请先上传历史CSV')
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'history.csv';path.write_bytes(file.getvalue())
                nums=read_history(path)
            report=study_historical_operators(nums,maximum=maximum)
            st.session_state['v32_report']={'history':report,'tables':None}
            tables=None
        if tables is not None:
            results=[]
            for label,table in tables.items():
                record=infer_new_categories(table,source_id=label,
                                            max_exceptions=max_exceptions,min_saved_bits=min_saved)
                results.append({'label':label,'result':record})
            st.session_state['v32_report']={'history':None,'tables':results}
    except Exception as exc:
        st.error(f'数学研究未完成：{exc}')

report=st.session_state.get('v32_report')
if report:
    if report['history'] is not None:
        h=report['history']
        st.metric('发现并验证的新能力',h['new_abilities'])
        st.caption(f'训练前缀{h["training_periods"]}期，110期保留区间没有参与拟合')
        st.json(h)
        download=h
    else:
        info=report['tables']
        rows=[];operators=[]
        for entry in info:
            r=entry['result']
            rows.append({'表':entry['label'],'状态':r['status'],
                         '旧类别最短(bit)':r['old_best_bits'],
                         '新增能力':len(r['abilities']),
                         '尝试类别定义数':r['hypotheses_tested']})
            operators.extend(r['abilities'])
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        if operators:
            op=st.selectbox('已证明能力',operators,format_func=lambda x:f'{x.family} · {x.id}')
            st.json(op.card())
            m=run_operator_on_100k(op,(0,4),(0,))
            c1,c2,c3=st.columns(3)
            c1.metric('全部号码',f'{m["total"]:,}')
            c2.metric('研究性保留',f'{m["retained"]:,}')
            c3.metric('研究性剔除',f'{m["removed"]:,}')
        st.caption('V3.1已能更简洁表达的结果不会被重新记成全新能力。')
        download={'version':'v32','source':'合成或用户输入，未核验彩票官方数据',
                  'entries':[{**x['result'],'abilities':[a.card() for a in x['result']['abilities']],
                              'name':x['label']} for x in info]}
    st.download_button('下载科研证据与能力卡',json.dumps(download,ensure_ascii=False,indent=2,default=str),
                       file_name='PL5_V32_数学类别假设证据.json',mime='application/json')
