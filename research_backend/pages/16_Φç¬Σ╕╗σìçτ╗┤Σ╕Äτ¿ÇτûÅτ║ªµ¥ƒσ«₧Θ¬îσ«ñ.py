"""Research-only interactive representation and constraint discovery."""
import csv
import io
import json
import numpy as np
import pandas as pd
import streamlit as st
from pailie5.autolift_v28 import study, invent

st.set_page_config(page_title='PL5 V2.8 自主升维科研',layout='wide')
st.title('PL5 V2.8 · 自主升维算子与稀疏约束实验室')
st.caption('安全表达式组合 → 多维稀疏映射 → 贝叶斯分箱平滑 → 关系蒸馏 → 独立留出证伪')
st.warning('高维模型分配概率不是开奖设备的真实概率。实验不会修改ESSE正式规则；公平独立开奖下100注的单期命中概率仍为0.1%。')
with st.sidebar:
    upload=st.file_uploader('导入官方历史CSV（来源需自行核验）',type=['csv'])
    synthetic=st.selectbox('演示类型',['不使用演示数据','独立均匀合成','人为设置位置关联'])
    maximum=st.slider('每轮发明算子',2,24,12)
    seed=st.number_input('固定随机种子',0,4294967295,20261102)
    val=st.slider('开发验证期数',20,100,35)
    test=st.slider('封存留出期数',20,100,30)
    budget=st.slider('实验候选注数',1,100,100)
    alpha=st.slider('Dirichlet先验强度',20,500,120)

if st.button('自动创造并验证高维算子',type='primary'):
    try:
        if synthetic!='不使用演示数据':
            rng=np.random.default_rng(int(seed));rows=rng.integers(0,10,size=(190,5))
            if synthetic=='人为设置位置关联':rows[:,1]=rows[:,0]
            history=[''.join(map(str,row)) for row in rows]
            source=synthetic+'（非真实开奖）'
        elif upload is not None:
            data=list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))
            if not data or 'number' not in data[0]:raise ValueError('CSV必须包含number列')
            if all('issue' in d for d in data) and len({d['issue'] for d in data})!=len(data):raise ValueError('期号重复')
            if all('date' in d for d in data):
                if len({d['date'] for d in data})!=len(data):raise ValueError('日期重复')
                data.sort(key=lambda d:(d['date'],d.get('issue','')))
            elif all('issue' in d for d in data):data.sort(key=lambda d:d['issue'])
            history=[d['number'].strip() for d in data]
            source=upload.name+'（来源尚未自动核验）'
        else:raise ValueError('选择合成数据或导入真实历史CSV')
        with st.spinner('全空间创新查重、训练、验证、反例审计和独立解释器核验'):
            r=study(history,seed=int(seed),maximum=int(maximum),validation_periods=val,
                    test_periods=test,budget=budget,alpha=float(alpha))
        st.session_state['v28']=(r,source)
    except (ValueError,TypeError,KeyError) as exc:st.error(str(exc))

if 'v28' in st.session_state:
    r,source=st.session_state['v28']
    st.caption('历史来源：'+source)
    c1,c2,c3,c4=st.columns(4)
    c1.metric('生成表达式',r['generated'])
    c2.metric('非冗余算子',r['unique'])
    c3.metric('有效验证门槛','通过（仅研究）' if r['gate']['passed'] else '未通过 / 均匀回退')
    c4.metric('独立留出平均log增益',f"{r['holdout']['mean_log_gain']:.5f}")
    st.subheader('高维表达式压缩为少量软约束')
    st.dataframe(pd.DataFrame([{'算子':x['id'],'高维槽位':x['feature_dimension'],
      '蒸馏规则数':x['nonzero_distilled_clauses'],
      '验证平均log增益':x['validation']['mean_log_gain'],
      'p（近似）':x['validation']['one_sided_t_approx_p']} for x in r['experiments']]),
      hide_index=True,use_container_width=True)
    with st.expander('被选算子的数学表达、关系和UACP能力说明书'):
        st.write('进入实验评分：',r['selected_operator'] or '无；均匀回退')
        if r['selected_operator']:
            row=next(x for x in r['experiments'] if x['id']==r['selected_operator'])
            st.json({'math':row['spec'],'sparse_relations':row['distilled_relations']})
        st.json(r['independent_operator_crosscheck'])
    st.subheader('实验候选与随机基线')
    st.dataframe(pd.DataFrame({'实验号码':r['experimental_top_k'],
       '同注数随机对照':r['equal_budget_random_control']}),hide_index=True)
    st.download_button('下载完整研究报告JSON',json.dumps(r,ensure_ascii=False,indent=2),file_name='PL5_V28研究报告.json')
    st.info('留出数据被查看后，不得反复修改算子或种子，再把该数据作为未经使用的最终测试。新的科学证据应来自未来封存的预测。')
