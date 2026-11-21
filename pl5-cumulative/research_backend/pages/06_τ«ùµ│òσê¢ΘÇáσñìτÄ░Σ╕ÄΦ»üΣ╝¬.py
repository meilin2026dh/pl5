"""V0.6 research observatory. All buttons explicitly trigger work on click."""
import hashlib
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.fulltext import extract_pdf_bytes
from autoresearch.workflow_v06 import run_for_document
from autoresearch.formulas import emit_review_code
from pailie5.data import load_csv

st.set_page_config(page_title='PL5 · 算法科研实验室V0.6',layout='wide')
st.title('PL5 V0.6 · 算法创造、复现与证伪')
st.warning('所有算法结果为科研探索：100注单期公平基线0.1%，10期至少命中一次约0.9955%。文献中的低频模式并不意味着下一期更不可能发生。')
st.caption('受限表达式自主创造 → 双解释器复现 → 历史逐期测试 → 公平随机模拟 → 审计台账。自动生成的代码只供审查，不被执行。')
with LabStore('runtime/autoresearch.sqlite') as store:
    reg=ResearchRegistry(store.db)
    docs=reg.documents(100);algos=reg.algorithms(100);audits=reg.audits(50)
    col=st.columns(3)
    col[0].metric('研究文献',len(docs));col[1].metric('创制公式',len(algos));col[2].metric('审计实验',len(audits))
    st.subheader('① 导入论文全文或研究材料')
    f=st.file_uploader('本地PDF、TXT或Markdown',type=['pdf','txt','md'])
    doc_key=st.text_input('文献编号（需唯一）',value='local-paper-001')
    title=st.text_input('文献标题',value='自主研究导入')
    if st.button('保存研究文献',disabled=f is None):
        try:
            raw=f.getvalue()
            if len(raw)>8_000_000:raise ValueError('文件超过8MB限制')
            if f.name.lower().endswith('.pdf'):text=extract_pdf_bytes(raw)
            else:text=raw.decode('utf-8-sig')[:70000]
            result=reg.add_document(doc_key,title,text,kind='local')
            st.success('文献入库');st.json(result);st.rerun()
        except Exception as e:st.error(str(e))
    if st.button('从已有V0.5论文库导入最多5条摘要'):
        count=0
        for p in store.papers(limit=5,min_score=2):
            if len(p['abstract'].strip())>=30:
                reg.add_document('lead:'+p['key'],p['title'] or p['key'],p['abstract'],url=p['url'],kind='abstract')
                count+=1
        st.success(f'导入{count}份摘要线索；摘要不等于全文。');st.rerun()
    docs=reg.documents(100)
    if docs:
        st.dataframe(pd.DataFrame(docs)[['doc_key','title','kind','text_length']],hide_index=True,use_container_width=True)
        selected=st.selectbox('选定研究材料',[x['doc_key'] for x in docs])
        st.subheader('② 自主生成新的复合指标算法')
        limit=st.slider('本轮自动创制数量',1,8,3)
        if st.button('自动生成算法并入候选库'):
            d=reg.get_document(selected)
            from autoresearch.formulas import invent_from_text
            result=[]
            for a in invent_from_text(d['text_excerpt'],selected,limit=limit):result.append(reg.add_algorithm(a,selected))
            st.success(f'创制{len(result)}种公式候选（可能已有相同指纹）');st.json(result);st.rerun()
    algos=reg.algorithms(100)
    if algos:
        chosen=st.selectbox('选定算法指纹',[x['fingerprint'] for x in algos])
        a=reg.get_algorithm(chosen)
        st.code(emit_review_code(a.formula),language='python')
        st.caption('代码文本仅用于审查；实际实验由安全AST解释器运行。')
        st.subheader('③ 独立复现与反证实验')
        file=st.file_uploader('已核验的官方历史开奖CSV，含period,number',type=['csv'],key='v06history')
        source=st.text_input('官方来源声明',placeholder='official:已人工对照官方公告')
        k=st.number_input('候选注数',1,100,100)
        evalsize=st.slider('开发集逐期回测期数',20,300,60)
        nulls=st.slider('公平随机对照模拟组数',0,8,3)
        if st.button('开始双路复现与公平随机反证',disabled=file is None):
            try:
                from autoresearch.verification import full_audit
                if not(source.startswith('official:') or source.startswith('https://')):raise ValueError('请声明官方数据来源')
                content=file.getvalue();draws=load_csv(content)
                if any('补零' in w for w in draws.warnings):raise ValueError('发现CSV前导零异常')
                if len(draws.frame)<56:raise ValueError('至少56期数据')
                result=full_audit(a,draws.frame['number'].tolist(),k=int(k),eval_size=evalsize,
                                  null_sequences=nulls,attempts=reg.audit_attempts())
                audit=reg.add_audit(chosen,hashlib.sha256(content).hexdigest(),result)
                st.success('完成审计记录；不代表预测优势。');st.json({'audit':audit,'report':result})
            except Exception as e:st.error(str(e))
    st.subheader('④ 研究审计档案')
    if audits:
        rows=[]
        for row in audits:
            rep=row['report'];rows.append({'audit_id':row['id'],'algorithm':row['fingerprint'],
                'time':row['created_at'],'replicated':rep.get('engineering_reproduced'),
                'hits':rep.get('development',{}).get('hits'),'n':rep.get('development',{}).get('n')})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.info('正式研究库收录需要在终端使用approve-research明确审批。工程通过也不自动进入现有过滤策略；预测效力必须另行前向验证。')
