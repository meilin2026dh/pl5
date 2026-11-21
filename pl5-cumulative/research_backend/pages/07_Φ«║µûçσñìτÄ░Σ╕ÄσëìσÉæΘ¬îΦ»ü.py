"""Optional Streamlit UI: click-to-run experiments, never automatic bets."""
import hashlib
from pathlib import Path
import streamlit as st
import pandas as pd
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.paper_protocol_v07 import build_research_protocol
from autoresearch.novelty_v07 import invent_diverse
from autoresearch.forward_v07 import forward_report,freeze_checked
from autoresearch.prospective import settle_from_history
from autoresearch.verification import rank_research_approved
from pailie5.data import load_csv

st.set_page_config(page_title='PL5 · V0.7科研审计',layout='wide')
st.title('PL5 V0.7 · 论文方法审计、指标创新与前向验证')
st.warning('研究平台不保证中奖。100注/期的公平随机命中概率为0.1%；10期至少一次约0.9955%。')
st.caption('论文适配不等于忠实复现；新颖度不是预测力；本地封存时间戳不能独立证明开奖前提交。')
with LabStore('runtime/autoresearch.sqlite') as store:
    r=ResearchRegistry(store.db)
    st.subheader('① 论文研究卡与特征去重')
    docs=r.documents(100)
    if docs:
        selected=st.selectbox('研究来源',[x['doc_key'] for x in docs])
        c1,c2=st.columns(2)
        with c1:
            if st.button('生成论文研究与复现实验计划'):
                st.json(build_research_protocol(r.get_document(selected)))
        with c2:
            if st.button('自动发现非冗余的新指标'):
                previous=[r.get_algorithm(x['fingerprint']) for x in r.algorithms(80)]
                candidates,review=invent_diverse(r.get_document(selected)['text_excerpt'],selected,
                                                  limit=3,already=previous,search_budget=24)
                res=[r.add_algorithm(a,selected) for a in candidates]
                st.json({'registered':res,'novelty':review})
    else:st.info('请先在06页面导入文献全文，或运行 research_v06.py ingest-leads。')
    st.subheader('② 开奖前封存 ≤100 注（必须人工明确执行）')
    f=st.file_uploader('开奖历史CSV，period,number',type=['csv'],key='v07_csv')
    source=st.text_input('官方开奖来源声明',value='official:人工核验官方公告')
    period=st.text_input('待预测期号（该期不能已经存在于所上传CSV）',value='')
    k=st.number_input('候选注数K',min_value=1,max_value=100,value=100)
    approved=[x for x in r.algorithms(300) if x['state']=='research_approved']
    st.caption(f'已通过人工审批进入研究库的算法：{len(approved)}条；未获审批的不参与排名。')
    if st.button('我确认当前期未开奖，生成并封存研究候选集'):
        try:
            if f is None:raise ValueError('缺少历史CSV')
            if not(source.startswith('official:') or source.startswith('https://')):raise ValueError('请填写来源')
            if not approved:raise ValueError('目前没有人工审批通过的研究算法')
            draws=load_csv(f.getvalue())
            if any('补零' in w for w in draws.warnings):raise ValueError('号码前导零缺失')
            if len(approved)>24:raise ValueError('算法数量超过单次限制24')
            models=[r.get_algorithm(x['fingerprint']) for x in approved]
            candidates,info=rank_research_approved(models,draws.frame['number'].tolist(),k=int(k))
            algo_hash=hashlib.sha256(str(sorted(m.fingerprint() for m in models)).encode()).hexdigest()
            result=freeze_checked(store.db,draws_frame=draws.frame,target_period=period,
                candidates=candidates,history_sha256=hashlib.sha256(f.getvalue()).hexdigest(),
                algorithm_sha256=algo_hash,official_source=source)
            st.success('本地封存成功（不等于第三方可信开奖前证明）')
            st.json({'commitment':result,'ranking':info})
            st.dataframe(pd.DataFrame({'rank':list(range(1,len(candidates)+1)),'number':candidates}),hide_index=True)
        except Exception as exc:st.error(str(exc))
    st.subheader('③ 新开奖入库后结算')
    if st.button('使用已上传CSV结算封存期号'):
        try:
            if f is None:raise ValueError('需要上传包含新增开奖号码的CSV')
            draws=load_csv(f.getvalue())
            if any('补零' in w for w in draws.warnings):raise ValueError('号码前导零缺失')
            out=settle_from_history(store.db,period_to_number=dict(zip(draws.frame['period'].astype(str),draws.frame['number'])),
                data_sha256=hashlib.sha256(f.getvalue()).hexdigest(),source_description=source)
            st.json(out)
        except Exception as exc:st.error(str(exc))
    st.subheader('④ 长期前向检验审计')
    if st.button('刷新前向验证报告'):
        st.json(forward_report(store.db))
    st.info('报告中的e-value仅在每期候选集确实开奖前确定、开奖公平独立且结果全部完整登记时具备所述统计含义。')
