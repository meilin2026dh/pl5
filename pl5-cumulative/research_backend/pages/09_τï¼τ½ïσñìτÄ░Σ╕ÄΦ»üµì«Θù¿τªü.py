"""PL5 V0.9 UI for source-traceability, built-in cross checks and FWER ledger."""
import streamlit as st
from autoresearch.store import LabStore
from autoresearch.replication_v09 import ReplicationRegistry,verify_independent_kernels
from autoresearch.evidence_v09 import EvidenceLedger
from autoresearch.pair_review_v09 import PairReview

st.set_page_config(page_title='PL5 V0.9 科研证据门禁',layout='wide')
st.title('PL5 V0.9 · 独立复现与统计证据门禁')
st.warning('彩票10万注公平等概率条件下，100注/期单期命中率为0.1%，10期内至少命中一次约0.9955%。算法增加不能自动突破此基线。')
st.caption('此页面的独立复现是对三种内置特征的纯Python/NumPy双实现核验；不代表任意论文或自动生成Python算法已被忠实复现。')

st.subheader('① 内置指标双实现核验')
method=st.selectbox('数学特征',['digit_sum','odd_count','transition_count'],format_func=lambda x:{'digit_sum':'5位数字和值','odd_count':'奇数数字个数','transition_count':'相邻数字变化次数'}[x])
if st.button('对10万注全部号码进行独立交叉计算'):
    try:
        with st.spinner('正在计算两套独立实现…'):
            st.json(verify_independent_kernels(method,exhaustive=True))
    except Exception as exc:st.error(str(exc))

with LabStore('runtime/autoresearch.sqlite') as db:
    protocols=ReplicationRegistry(db.db)
    ledger=EvidenceLedger(db.db)
    pairs=PairReview(db.db)
    st.subheader('② 文献—算法—验证协议')
    existing=protocols.list(100)
    if existing:
        st.dataframe(existing,hide_index=True)
        selected=st.selectbox('选择已登记的协议',[x['protocol_id'] for x in existing])
        if st.button('仅对内置数学方法执行交叉审计'):
            try:st.json(protocols.verify_builtin(selected))
            except Exception as exc:st.error(str(exc))
    else:st.info('尚无V0.9复现协议。先在V0.8登记算法，再通过 research_v09.py protocol-create 绑定文献出处、公式定位、假设和参考样例。')
    st.subheader('③ 开放Python算法配对复现（仅人工审批Docker执行）')
    pair_records=pairs.list()
    if pair_records:
        st.dataframe([{k:r[k] for k in ('pair_id','protocol_id','reviewer','created_at')} for r in pair_records],hide_index=True)
        st.caption('请通过 research_v09.py pair-audit --allow-docker 运行，未授权时不会执行任何外部代码。')
    else:st.info('尚无独立代码对。可通过CLI人工登记第二份不同代码的来源与审查理由。')
    st.subheader('④ 模型家族的全局统计证据')
    report=ledger.family_report()
    a,b,c=st.columns(3)
    a.metric('模型研究系列',report['models_registered'])
    b.metric('全家族错误概率预算',f"{report['family_alpha_total']:.1%}")
    c.metric('已配置预算',f"{report['alpha_spent']:.2%}")
    if report['models']:
        st.dataframe([{k:v for k,v in r.items() if k in ('model_id','series_index','alpha_allocated','total_commits','verified_prefix','hits_in_prefix','expected_hits_fair','evidence_threshold_crossed')} for r in report['models']],hide_index=True)
        with st.expander('完整科研证据'):
            st.json(report)
    else:st.info('尚无预注册验证系列。请先完成算法研究协议并在CLI中登记模型，封存开奖前候选集。')
    st.error('安全边界：本地SQLite哈希/时间戳不能证明真实开奖前封存，官方结果来源需另行核验。任何过门槛结果都不能自动进入正式选号模型。')
