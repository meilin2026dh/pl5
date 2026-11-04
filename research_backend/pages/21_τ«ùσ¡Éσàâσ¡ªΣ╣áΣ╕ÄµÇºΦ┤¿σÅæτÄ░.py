"""PL5 V3.3 Streamlit math learning lab. No automatic promotion."""
import json,sys
from pathlib import Path
import numpy as np
import streamlit as st
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pailie5.operator_metalearning_v33 import learn,fixtures,PROPERTIES

st.set_page_config(page_title='PL5 · 算子元学习 V3.3',layout='wide')
st.title('V3.3 算子结构与参数元学习实验室')
st.caption('仅在10×10数学真值表上研究；不自动投注，不代表发现中奖规律。')
example=st.selectbox('研究样本',list(fixtures())+['上传10×10 JSON数学表'])
file=st.file_uploader('上传数学表（JSON二维数组）',type='json') if example.startswith('上传') else None
seed=st.number_input('学习随机种子',value=20261102,step=1,min_value=0,max_value=2**32-1)
required=st.multiselect('要求被证明的数学性质（不满足会直接拒绝）',list(PROPERTIES))
maximum=st.slider('最多显示通过严格核验的新算子数',1,10,5)
if st.button('运行结构与参数学习',type='primary'):
    try:
        if example.startswith('上传'):
            if file is None:st.error('请先上传JSON');st.stop()
            if file.size>1_000_000:raise ValueError('文件过大')
            table=np.asarray(json.loads(file.read().decode('utf-8-sig')))
        else:table=fixtures()[example]
        result=learn(table,seed=int(seed),required_properties=required,maximum=maximum,source_id=example)
        st.metric('全域精确通过的压缩能力',len(result['abilities']))
        st.write('最终状态：',result['status'])
        st.write('性质校验：',result['properties'])
        st.write('原始真值表');st.dataframe(table,use_container_width=True)
        st.write('训练期与留出表格单元诊断');st.dataframe(result['trials'],use_container_width=True)
        cards=[v.card() for v in result['abilities']]
        for c in cards:
            with st.expander(f"{c['family']} · {c['description_bits_proxy']} bit · {c['id']}"):
                st.json(c)
        st.download_button('下载可复核报告',json.dumps({**result,'abilities':cards},ensure_ascii=False,indent=2),
                           'V33_math_research.json','application/json')
        st.warning('留出的是运算表单元，不是开奖时间外样本；数学压缩不代表预测优势。')
    except (ValueError,TypeError,KeyError,UnicodeDecodeError) as exc:
        st.error(f'数学表或参数格式错误：{exc}')
