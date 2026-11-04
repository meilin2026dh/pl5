"""Research UI: High dimensional lifts, no predictive advantage claims."""
from __future__ import annotations
import csv
import io
import json
import numpy as np
import pandas as pd
import streamlit as st
from pailie5.highdim_v26 import study, capabilities, proposals

st.title('PL5 · HDSE高维隐结构发现实验室 V2.6')
st.caption('高阶张量（最多11,050坐标） · 时空状态（最多5,550坐标） · 有限群傅里叶谱（最多8,145个字符候选）')
st.warning('数学升维不能凭空创造未来开奖信息。每个候选集合必须与同注数均匀随机基线比较；研究分数不等于真实中奖概率。')
with st.sidebar:
    seed=st.number_input('随机种子',0,4294967295,20261102)
    maximum=st.slider('模型假设数量',1,12,7)
    test_periods=st.slider('独立历史留出期数',20,100,30)
    budget=st.slider('实验候选数量',1,100,100)
    null_trials=st.slider('完整流程IID随机对照次数（较耗时）',0,10,2)
    upload=st.file_uploader('官方数据CSV（number列）',type=['csv'])
    synthetic=st.checkbox('仅使用IID合成数据演示',value=False)

with st.expander('算法能力说明书',expanded=False):
    st.dataframe(pd.DataFrame([{'ID':x['id'],'模型':x['spec']['family'],
     '阶数':x['spec']['order'],'标称特征维度':x['declared_feature_coordinates'],
     '状态':x['status']} for x in capabilities()]),hide_index=True)
if st.button('生成高维研究假设'):
    st.session_state['hdse_proposals']=[x.capability() for x in proposals(int(seed),int(maximum))]
if 'hdse_proposals' in st.session_state:
    st.dataframe(pd.DataFrame([{'算法':v['id'],'族':v['spec']['family'],
     '阶':v['spec']['order'],'特征维度':v['declared_feature_coordinates']} for v in st.session_state['hdse_proposals']]),hide_index=True)

if st.button('执行时间外验证及零假设模拟',type='primary'):
    try:
        if synthetic:
            h=[f'{x:05d}' for x in np.random.default_rng(int(seed)).integers(100000,size=320)]
            source='IID synthetic demonstration'
        elif upload is not None:
            data=list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))
            if not data or 'number' not in data[0]:raise ValueError('CSV缺少number列')
            if 'date' in data[0]:data.sort(key=lambda x:(x['date'],x.get('issue','')))
            elif 'issue' in data[0]:data.sort(key=lambda x:x['issue'])
            if 'issue' in data[0] and len({r['issue'] for r in data})!=len(data):raise ValueError('重复期号')
            h=[r['number'].strip() for r in data]
            source=upload.name+'（用户提供，需确认官方来源）'
        else:raise ValueError('需要上传经核验的官方CSV或显式勾选合成演示')
        out=study(h,seed=int(seed),maximum=int(maximum),test_periods=int(test_periods),
                  budget=int(budget),null_trials=int(null_trials))
        out['source']=source
        st.session_state['hdse_report']=out
    except (ValueError,TypeError) as exc: st.error(str(exc))

if 'hdse_report' in st.session_state:
    r=st.session_state['hdse_report']
    st.metric('模型选择', '均匀基线回退' if r['uniform_fallback'] else r['selected']['spec']['family'])
    st.metric('历史留出平均log增益 (nats/期)',f"{r['holdout']['mean_log_gain']:.6f}")
    st.metric('公平单期覆盖率',f"{r['fair_probability_exact']*100:.3f}%")
    st.dataframe(pd.DataFrame([{'模型':x['spec']['family'],'阶':x['spec']['order'],
        '验证增益':x['validation_gain'],'均匀混合λ':x['chosen_lambda']} for x in r['hypotheses']]),hide_index=True)
    if 'null_controls' in r:st.json(r['null_controls'])
    st.dataframe(pd.DataFrame({'研究候选':r['experimental_top_k'],
                               '等注数随机对照':r['equal_budget_random_control']}),hide_index=True)
    st.download_button('导出独立实验报告',json.dumps(r,ensure_ascii=False,indent=2),file_name='HDSE_V26_研究报告.json')
    st.download_button('导出候选CSV','number,group\n'+ '\n'.join(f'{n},experimental' for n in r['experimental_top_k'])+'\n'+ '\n'.join(f'{n},random_control' for n in r['equal_budget_random_control']),file_name='HDSE_V26_候选对照.csv')
    st.info('留出结果属于已查看历史测试，不能循环调参后继续声称独立。未来前向开奖才可积累新的独立证据。')
