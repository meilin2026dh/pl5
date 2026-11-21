"""V2.5 presentation; no automatic publishing or external execution."""
import json
import csv
import io
import streamlit as st
import pandas as pd
from pailie5.representation_v25 import propose, audit, study

st.title('PL5 · 自主表示空间发现实验室 V2.5')
st.info('研究性空间创新：新特征不改变公平彩票每注1/100000的真实开奖概率。')
with st.sidebar:
    st.subheader('创新实验参数')
    seed=st.number_input('固定随机种子',0,4294967295,20261102)
    count=st.slider('数学变换提案数量',1,60,16)
    test_periods=st.slider('历史留出期数',20,100,30)
    alpha=st.number_input('Dirichlet结构先验强度',1.,1000.,100.)
    uploaded=st.file_uploader('导入已核验的历史开奖 CSV (number列)',type='csv')
    demo=st.checkbox('使用合成演示数据',value=False)

if st.button('自主生成空间 · 全量去冗余',type='primary'):
    st.session_state.v25_audit=audit(propose(int(seed),int(count)))

if 'v25_audit' in st.session_state:
    a=st.session_state.v25_audit
    st.metric('工程候选',a['accepted'])
    st.dataframe(pd.DataFrame([{'id':x['id'],'算子':x['spec']['operator'],
            '状态':x['status'],'桶数':x['bucket_count'],'信息熵(bits)':x['entropy_bits'],
            '等价于':x['equivalent_to']} for x in a['reviewed']]),hide_index=True)
    st.download_button('导出能力审计JSON',json.dumps(a,ensure_ascii=False,indent=2),file_name='V25_能力审计.json')

if st.button('独立时间切分实验'):
    try:
        if uploaded is not None and not demo:
            rows=list(csv.DictReader(io.StringIO(uploaded.getvalue().decode('utf-8-sig'))))
            if not rows or 'number' not in rows[0]:raise ValueError('CSV必须包含number列')
            if 'date' in rows[0]:rows.sort(key=lambda x:(x['date'],x.get('issue','')))
            elif 'issue' in rows[0]:rows.sort(key=lambda x:x['issue'])
            history=[r['number'].strip() for r in rows]
        elif demo:
            history=[f'{(7919*i+17*i*i)%100000:05d}' for i in range(160)]
            st.warning('演示数据为合成序列，不是官方开奖结果')
        else:
            raise ValueError('请导入官方CSV或明确勾选合成演示数据')
        st.session_state.v25_study=study(history,seed=int(seed),count=int(count),
                                          test_periods=int(test_periods),alpha=float(alpha))
    except (ValueError,TypeError) as e:
        st.error(str(e))

if 'v25_study' in st.session_state:
    r=st.session_state.v25_study
    s=r.get('selected_capability')
    if s:
        st.write('选出的研究特征',s['spec'])
        st.write('历史留出（仅一次实验评估）：',r['historical_holdout'])
        st.caption('留出集用于查看结果，不允许重新用此成绩反复选模并宣称未见测试')
        st.dataframe(pd.DataFrame({'实验性Top100':r['next_draw_exploratory_top100'],
                                   '等注数随机对照':r['next_draw_random_control_100']}))
        st.download_button('下载完整研究报告',json.dumps(r,ensure_ascii=False,indent=2),file_name='V25_实验报告.json')
