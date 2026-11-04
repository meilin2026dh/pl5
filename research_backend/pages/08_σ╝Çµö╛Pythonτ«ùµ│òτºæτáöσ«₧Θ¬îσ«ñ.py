"""Research-only Streamlit UI; no automatic Python execution outside Docker."""
from hashlib import sha256
import streamlit as st
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.python_lab_v08 import PythonResearchStore,docker_available,inspect_python_source
from autoresearch.proposals_v08 import offline_proposals,llm_python_proposal
from pailie5.data import load_csv

st.set_page_config(page_title='PL5 V0.8 · 开放算法实验室', layout='wide')
st.title('PL5 V0.8 · 自主算法创造、沙箱复现与证伪')
st.warning('仅供科研验证：随机开奖下100注的单期中奖概率为0.1%。历史模式罕见不意味着未来延续概率降低。')
st.caption('自动生成的是论文启发的实验假设，并不自动等于论文原方法的忠实复现；生成代码不在PL5主进程中执行。')
with LabStore('runtime/autoresearch.sqlite') as store:
    registry=ResearchRegistry(store.db)
    lab=PythonResearchStore(store.db)
    st.subheader('1. 文献 → 可运行Python假设')
    documents=registry.documents(100)
    if not documents:
        st.info('请先在06页面导入论文文本/PDF或文献研究线索。')
    else:
        doc_id=st.selectbox('选择研究文献',[x['doc_key'] for x in documents])
        c1,c2=st.columns(2)
        with c1:
            if st.button('离线生成两个开放Python实验模型'):
                specs=offline_proposals(registry.get_document(doc_id))
                st.json([lab.add(document_key=doc_id,**s) for s in specs])
        with c2:
            llm_permission=st.checkbox('我允许此次调用付费大模型进行Python算法提案')
            if st.button('使用大模型提出新的Python算法（可选）'):
                if not llm_permission:st.error('请先确认付费调用授权。')
                else:
                    try:
                        spec=llm_python_proposal(registry.get_document(doc_id))
                        st.json(lab.add(document_key=doc_id,**spec))
                    except Exception as e:st.error(str(e))
        source_text=st.text_area('或手动提交研究代码（仅score_batch接口）',height=140)
        claim=st.text_input('研究假设和限制声明（至少10字）')
        if st.button('登记我提供的Python代码（只作静态检查，不运行）'):
            try:st.json(lab.add(document_key=doc_id,source=source_text,origin='human',method_claim=claim))
            except Exception as e:st.error(str(e))
    st.subheader('2. 算法代码审查')
    items=lab.list()
    if not items:st.info('尚无V0.8开放式Python算法候选。')
    else:
        cid=st.selectbox('待审核的算法代码哈希',[x['id'] for x in items],
                         format_func=lambda x:x[:16]+'…')
        candidate=lab.get(cid)
        st.code(candidate['source'],language='python')
        st.caption(candidate['method_claim'])
        st.json(inspect_python_source(candidate['source']))
        st.subheader('3. Docker隔离复现与逐期回测')
        if docker_available():st.success('Docker引擎可用，仍需要手动确认后才会执行。')
        else:st.error('Docker引擎当前不可用。出于安全考虑，系统不会在本地Python进程直接执行未知算法。')
        upload=st.file_uploader('历史开奖CSV（period,number，官方数据需自行核验）',type=['csv'])
        official_source=st.text_input('官方开奖核验来源声明',value='official:人工核验官方公告')
        k=st.number_input('研究候选数量',min_value=1,max_value=100,value=100)
        n=st.number_input('最近开发回测期数',min_value=2,max_value=24,value=8)
        allow=st.checkbox('已阅读代码并同意只在隔离Docker容器中执行本次研究')
        if st.button('执行两次隔离复现 + 逐期开发回测'):
            try:
                if not allow:raise PermissionError('需要明确授权沙箱运行')
                if upload is None:raise ValueError('请先上传数据')
                if not(official_source.startswith('official:') or official_source.startswith('https://')):
                    raise ValueError('请填写官方来源核验声明')
                raw=upload.getvalue()
                draws=load_csv(raw)
                if any('补零' in w for w in draws.warnings):raise ValueError('号码补零风险，请人工核验')
                st.json(lab.audit(cid,draws.frame['number'].tolist(),data_digest=sha256(raw).hexdigest(),
                                  k=int(k),eval_size=int(n),official_source=official_source))
            except Exception as e:st.error(str(e))
    st.info('审计通过只代表工程/可重复性测试通过；绝不自动部署到正式选号系统。')
