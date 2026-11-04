"""PL5 V3.1 visual lab; frozen operator categories, all-domain verification."""
from pathlib import Path
import json
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st
from pailie5.primitive_categories_v31 import (
    invent_categories, category_gap_report, run_operator_on_100k,
    CategoryRegistry, analyze_v29_primitives,
)
from research_v24 import read_history

st.set_page_config(page_title='PL5 V3.1 算子类别自发现', layout='wide')
st.title('PL5 V3.1 · 数学算子类别自主扩展')
st.caption('新能力发现：从100格有限运算表中寻找更短的商类/轨道定义；核验后登记到AAN科研库。')
st.warning('数学等价与描述长度压缩不等于彩票开奖预测规律。所有新运算均处于research_only，不会自动用于正式过滤。')
mode = st.radio('研究输入', ['预置数学对照实验', '上传10×10运算表JSON', '历史CSV诱导V2.9算子再发明类别'], horizontal=True)
maximum = st.slider('历史研究最多分析的基础算子数', 1, 20, 5)
upload = st.file_uploader('选择输入文件（CSV应事先核验是否来自官方）', type=['json'] if mode.startswith('上传') else ['csv']) if mode != '预置数学对照实验' else None
if st.button('发明算子类别并全域验证', type='primary', use_container_width=True):
    try:
        if mode == '预置数学对照实验':
            a,b=np.indices((10,10))
            oracle=np.array([0,2,1,0,1,2,2,1,0,2],dtype=np.uint8)
            rng=np.random.default_rng(20261102)
            noise=rng.integers(0,4,(10,10),dtype=np.uint8);noise.ravel()[:4]=np.arange(4)
            tables={'行列商类合成结构':((a%2+b%3)%3).astype(np.uint8),
                    '循环差合成结构':oracle[(a-b)%10], '随机非结构对照':noise}
            report={'source':'明确标注的数学合成夹具', 'items':[]}
            for name,t in tables.items():
                cs,_=invent_categories(t,source_id=name)
                report['items'].append({'name':name,'gap':category_gap_report(t,source_id=name),'operators':cs})
        elif mode.startswith('上传'):
            if not upload:raise ValueError('请先上传运算表JSON')
            t=np.asarray(json.loads(upload.getvalue().decode('utf-8-sig')))
            cs,_=invent_categories(t,source_id='用户提供的数学表')
            report={'source':'用户提供数学表','items':[{'name':'上传的数学表','gap':category_gap_report(t),'operators':cs}]}
        else:
            if not upload:raise ValueError('请先上传历史数据')
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'history.csv';p.write_bytes(upload.getvalue());h=read_history(p)
            study=analyze_v29_primitives(h,maximum=maximum)
            report={'source':'用户提供的历史CSV，未独立核验官方来源','history_study':study,'items':[]}
        st.session_state['v31_study']=report
    except Exception as e: st.error(f'未完成研究：{e}')

rep=st.session_state.get('v31_study')
if rep:
    st.caption(f'数据来源：{rep["source"]}')
    if 'history_study' in rep:
        r=rep['history_study']
        st.metric('已发现新的可压缩类别能力',r['generated'])
        st.dataframe(pd.DataFrame([{'原算子':x['operator_id'], '新类别':x['category']['family'],
                                     '描述位数代理':x['category']['representation_bits_proxy'],
                                     '可注册为新研究能力':x['new_coding_value']} for x in r['cards']]),
                     use_container_width=True, hide_index=True)
        st.json(r['language_gaps'])
        payload=r
    else:
        rows=[]; operators=[]
        for r in rep['items']:
            if not r['operators']:
                rows.append({'表':r['name'],'发现':'无可压缩类别','编码收益':0})
            for op in r['operators']:
                operators.append(op)
                rows.append({'表':r['name'],'发现':op.family, '编码收益':op.raw_bits-op.representation_bits})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        payload={'source':rep['source'],'items':[
            {'name':r['name'],'gap':r['gap'],'abilities':[op.card() for op in r['operators']]} for r in rep['items']]}
        if operators:
            op=st.selectbox('查看算法能力说明书',operators,format_func=lambda x:x.id)
            st.json(op.card())
            samples = run_operator_on_100k(op,(0,4),(0,))
            a,b,c=st.columns(3)
            a.metric('逐号计算',f'{samples["total"]:,}')
            b.metric('实验保留',f'{samples["retained"]:,}')
            c.metric('实验排除',f'{samples["removed"]:,}')
            st.caption('此规则仅用于展示完整十万注二值掩码，未根据彩票预测表现学习启用权重。')
    st.download_button('下载完整数学研究记录',json.dumps(payload,ensure_ascii=False,indent=2,default=str,allow_nan=False),
                       file_name='PL5_V31_operator_category_research.json',mime='application/json')
