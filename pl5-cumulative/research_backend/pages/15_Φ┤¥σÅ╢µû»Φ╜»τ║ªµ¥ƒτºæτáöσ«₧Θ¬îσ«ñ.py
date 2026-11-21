"""PL5 V2.7 interactive constrained-Bayes research workbench."""
import csv
import io
import json
import numpy as np
import pandas as pd
import streamlit as st
from pailie5.bcse_v27 import study, capabilities, DEFAULT_CONSTRAINTS, full_diagnostics

st.set_page_config(page_title='PL5 · BCSE V2.7',layout='wide')
st.title('PL5 V2.7 · 贝叶斯软约束雕塑实验室')
st.caption('历史频率贝叶斯基线 · 多空间约束 · 约束权重后验 · 后验可信区间 · 严格时间留出')
st.warning('数学违例是确定性事件；后验概率描述指定研究模型的不确定性，不是开奖设备的真实中奖概率。公平开奖下100注单期概率仍为0.1%。')

labels={'step_large':'邻位绝对步长达到阈值','route_zero_absent':'五位均无0路数字',
        'parity_extreme':'五位全奇或全偶','sum_tail_repeat':'近期连续3期和值尾重复，再延续',
        'sum_arithmetic':'近期3期和值非零等差，再延续',
        'position_repeat':'某位置最近3期重复，再延续'}
with st.sidebar:
    upload=st.file_uploader('导入核验来源的官方开奖CSV',type=['csv'])
    demo=st.checkbox('使用IID均匀合成数据（仅演示）',False)
    st.subheader('约束选择与模型')
    kinds=st.multiselect('启用约束',options=list(labels),default=list(labels),format_func=lambda s:labels[s])
    threshold=st.slider('邻位绝对差阈值',1,9,7)
    alpha=st.slider('历史位置Dirichlet先验总强度',10,200,30)
    valperiod=st.slider('独立开发验证期数',20,100,35)
    testperiod=st.slider('封存留出期数',20,100,30)
    budget=st.slider('最终实验候选注数',1,100,100)
    seed=st.number_input('随机种子',min_value=0,max_value=4294967295,value=20261102)
    null_trials=st.slider('IID完整流程零假设重跑',0,2,0)

with st.expander('UACP算法能力说明书'):
    st.dataframe(pd.DataFrame([{'ID':x['id'],'类型':labels.get(x['type'],x['type']),
        '输入':'开奖前历史与全部号码','输出':'100000位违例掩码','验证':'实验性'} for x in capabilities()]),
        hide_index=True,use_container_width=True)

if st.button('执行贝叶斯软约束实验',type='primary'):
    try:
        if not kinds:raise ValueError('至少选择一个约束')
        constraints=[{'id':k,'kind':k,**({'threshold':threshold} if k=='step_large' else {})} for k in kinds]
        if demo:
            values=np.random.default_rng(int(seed)).integers(100000,size=190)
            hist=[f'{n:05d}' for n in values]
            source='IID合成数据（非真实开奖）'
        elif upload is not None:
            reader=csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig')))
            if not reader.fieldnames or 'number' not in reader.fieldnames:raise ValueError('CSV必须有number列，建议issue,date,number')
            items=list(reader)
            if 'issue' in reader.fieldnames and len({x['issue'] for x in items})!=len(items):raise ValueError('期号重复')
            if 'date' in reader.fieldnames and len({x['date'] for x in items})!=len(items):raise ValueError('开奖日期重复')
            if 'date' in reader.fieldnames:items.sort(key=lambda r:(r['date'],r.get('issue','')))
            elif 'issue' in reader.fieldnames:items.sort(key=lambda r:r['issue'])
            hist=[v['number'].strip() for v in items]
            source=f'{upload.name}（用户上传，需确认官方来源）'
        else:raise ValueError('请上传官方CSV，或显式选择IID合成演示')
        with st.spinner('构造全部10万注违例掩码，并依次开展训练/验证/留出测试'):
            result=study(hist,constraints=constraints,budget=int(budget),seed=int(seed),
                         validation_periods=int(valperiod),test_periods=int(testperiod),
                         dirichlet_alpha=float(alpha),null_trials=int(null_trials))
        st.session_state['bcse_result']=(result,hist,constraints,source)
    except (ValueError,TypeError,KeyError) as exc: st.error(str(exc))

if 'bcse_result' in st.session_state:
    result,hist,constraints,source=st.session_state['bcse_result']
    st.caption('数据源：'+source)
    c1,c2,c3,c4=st.columns(4)
    c1.metric('独立验证是否通过','通过（仅研究）' if result['gate']['passed'] else '未通过：均匀回退')
    c2.metric('验证平均log增益',f"{result['validation']['mean_log_gain']:.5f}")
    c3.metric('最终留出平均log增益',f"{result['holdout']['mean_log_gain']:.5f}")
    c4.metric('公平随机单期覆盖率',f"{result['fair_hit_probability']*100:.3f}%")
    with st.expander('约束触发和相关性审计',expanded=True):
        st.dataframe(pd.DataFrame([{ '约束':labels.get(c['id'],c['id']), '当前违反号码数':c['count'],
            '触发比例':f"{c['fraction']:.3%}"} for c in result['next_draw_rule_flags']]),hide_index=True)
        if result['redundant_constraints']:st.json(result['redundant_constraints'])
        else:st.caption('未检测到需要合并的高正相关约束（检验只基于训练前缀对应掩码）')
    with st.expander('模型后验权重'):
        df=pd.DataFrame([{'模型':k,'后验权重':v} for k,v in result['posterior_model_weights_training'].items()]).sort_values('后验权重',ascending=False)
        st.dataframe(df.head(18),hide_index=True,use_container_width=True)
        st.caption(f"均匀模型后验质量：{result['gate']['posterior_uniform_mass']:.4f}。模型族使用预先固定的离散权重网格。")
    st.subheader('候选号码 · 后验评分与可信区间')
    items=pd.DataFrame(result['candidate_details'])
    st.dataframe(items,hide_index=True,use_container_width=True)
    st.caption('置信区间指模型后验可信区间，并不代表真实彩票开奖号码的95%预测覆盖率。下表只显示前30名；可导出完整10万注。')
    st.download_button('下载研究报告JSON',json.dumps(result,ensure_ascii=False,indent=2),file_name='PL5_BCSE_V27_研究报告.json')
    cand='number,group\n'+'\n'.join(f'{x},model_top_k' for x in result['experimental_top_k'])+'\n'+'\n'.join(f'{x},random_control' for x in result['equal_budget_random_control'])
    st.download_button('下载实验候选和随机对照CSV',cand,file_name='PL5_BCSE_V27_候选与对照.csv')
    if st.button('生成完整10万注评分＋后验区间CSV（可能耗时）'):
        with st.spinner('计算全量模型后验分布及可信区间'):
            order,f=full_diagnostics(hist,result,constraints)
            buf=io.StringIO();out=csv.writer(buf)
            out.writerow(['rank','number','posterior_model_mean','p_ci_low','p_ci_high',
                'penalty_mean','penalty_ci_low','penalty_ci_high','suppression_posterior_mass','violation_signature','uniform_baseline'])
            for ix,n in enumerate(order,1):
                out.writerow([ix,f'{int(n):05d}',f['model_probability_mean'][n],f['model_probability_ci_low'][n],
                    f['model_probability_ci_high'][n],f['penalty_mean'][n],f['penalty_ci_low'][n],
                    f['penalty_ci_high'][n],f['posterior_mass_below_uniform'][n],int(f['signature'][n]),1/100000])
            st.session_state['bcse_full_csv']=buf.getvalue()
    if 'bcse_full_csv' in st.session_state:
        st.download_button('下载完整100000注CSV',st.session_state['bcse_full_csv'],file_name='PL5_BCSE_V27_全部号码后验区间.csv',mime='text/csv')
    st.info('最终留出区间已经查看。重复改规则或阈值再选最好的一次，不构成新的独立验证；应以未来已封存期次继续检验。')
