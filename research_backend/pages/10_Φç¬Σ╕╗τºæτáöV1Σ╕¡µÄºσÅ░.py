"""Read-only V1.0 research operations overview. No background jobs start from this page."""
from pathlib import Path
import streamlit as st
import pandas as pd
from autoresearch.store import LabStore
from autoresearch.integrated_v10 import ResearchCoordinator

st.set_page_config(page_title='PL5 V1.0 科研中控台',layout='wide')
st.title('PL5 V1.0 · 自主科研中控台')
st.warning('这是研究管理平台，并非概率保证。公平开奖时每期100注的命中基线为0.1%；10期至少一次约0.996%。')
st.caption('工作流可恢复 · 原始论文与算法证据 · 预算上限 · 开奖前候选包本地完整性校验')
ROOT=Path(__file__).resolve().parents[1]
with LabStore(ROOT/'runtime'/'autoresearch.sqlite') as store:
    coordinator=ResearchCoordinator(store)
    runs=coordinator.status(limit=30)
    col1,col2,col3=st.columns(3)
    col1.metric('历史科研任务',len(runs))
    col2.metric('已完成任务',sum(x['status']=='completed' for x in runs))
    col3.metric('失败/等待恢复',sum(x['status']=='failed' for x in runs))
    if runs:
        st.dataframe(pd.DataFrame([{'任务ID':r['run_id'],'状态':r['status'],'创建':r['started_at'],
                                   '网络模式':r['config']['mode'],
                                   '预算请求上限':r['budget'].get('metadata_requests_max',0)} for r in runs]),
                     hide_index=True,use_container_width=True)
        selected=st.selectbox('查看任务与步骤', [r['run_id'] for r in runs])
        st.json(coordinator.status(selected))
    else:st.info('暂时没有V1.0研究任务。请先用终端运行 research_v10.py demo 或 run --offline-fixture。')
    st.subheader('算法封存包完整性')
    rows=[dict(r) for r in store.db.execute('SELECT * FROM v10_bundles ORDER BY created_at DESC LIMIT 20')] if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v10_bundles'").fetchone() else []
    if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else:st.caption('尚无已登记的本地候选包。真正的第三方开奖前可信时间证明仍需外部服务。')
    st.info('定时任务、付费模型、Docker外部代码执行、人工审批均为独立开关。该页面不会自行联网、运行算法或自动投注。')
