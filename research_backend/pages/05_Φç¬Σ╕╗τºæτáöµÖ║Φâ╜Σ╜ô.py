"""V0.5 research intake and limited algorithm lab. Streamlit UI reads the same SQLite store as CLI."""
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from autoresearch.store import LabStore
from autoresearch.lab import Hypothesis,walk_forward,rank_100
from autoresearch.prospective import precommit,outcome_report
from pailie5.data import load_csv
import hashlib

st.set_page_config(page_title='PL5 · 自主科研智能体',layout='wide')
st.title('PL5 · 自主科研智能体 V0.5')
st.caption('论文/开源线索自动发现 → 研究候选 → 逐期开发回测 → 影子验证 → 100注实验候选集')
st.warning('100注单期随机基线命中率0.1%；10期至少命中1次约0.9955%。本页结果不代表已验证预测优势，不自动投注。')
DB=Path('runtime/autoresearch.sqlite')
with LabStore(DB) as lab:
    all_papers=lab.papers(limit=300)
    hyps=lab.hypotheses(limit=300)
    trials=lab.trials(limit=80)
    a,b,c=st.columns(3)
    a.metric('已发现研究线索',len(all_papers))
    b.metric('已登记研究假设',len(hyps))
    c.metric('实验记录',len(trials))

    st.subheader('① 联网科研情报')
    st.caption('只请求OpenAlex、arXiv、GitHub的公开元数据，不执行远程仓库代码；需网络连接。')
    if st.button('立即执行论文及开源项目巡检'):
        try:
            from autoresearch.collectors import collect_all
            from autoresearch.lab import relevance_score
            with st.spinner('联系公开学术接口…'):
                papers,errors=collect_all(limit=3,providers=('openalex','arxiv','github'))
                added=lab.upsert_papers(papers,relevance_score)
                lab.record_cycle(len(papers),added,errors)
            st.success(f'检索到{len(papers)}条，新增{added}条；失败请求{len(errors)}条')
            if errors:st.dataframe(pd.DataFrame(errors))
            st.rerun()
        except Exception as e:st.error(str(e))
    if all_papers:
        st.dataframe(pd.DataFrame(all_papers)[['source','title','published','topic','score','url']],
                     hide_index=True,use_container_width=True)

    st.subheader('② 受限研究假设合成')
    st.caption('将研究主题映射成平台已有的指标与模式组合；是研究假设，不代表论文声称这些规则有效。')
    if st.button('从研究线索自动生成候选假设'):
        from autoresearch.lab import propose
        from autoresearch.collectors import Paper
        new=0
        for row in lab.papers(limit=50,min_score=2):
            p=Paper(row['key'],row['source'],row['title'],row['abstract'],row['url'],row['published'],row['topic'],row['authors'])
            for h in propose(p):new+=int(lab.add_hypothesis(h,row['key']))
        st.success(f'新增{new}个不同的研究假设；重复研究自动关联来源。')
        st.rerun()
    st.subheader('②b 大模型辅助论文阅读（可选、付费）')
    st.caption('点击后最多分析1篇尚未分析的论文元数据；需要自行设置OPENAI_API_KEY。只生成研究卡和受限配置，不能执行外部代码。')
    if st.button('明确同意本次大模型API调用并分析1篇'):
        import os
        if not os.environ.get('OPENAI_API_KEY'):
            st.error('尚未设置OPENAI_API_KEY；不会发起任何收费调用。')
        else:
            from autoresearch.collectors import Paper
            from autoresearch.llm import analyze_abstract
            todo=lab.papers_needing_analysis(limit=1,min_score=2)
            if not todo:st.info('没有符合条件且尚未分析的线索。')
            else:
                r=todo[0]
                p=Paper(r['key'],r['source'],r['title'],r['abstract'],r['url'],r['published'],r['topic'],r['authors'])
                try:
                    card,spec=analyze_abstract(p)
                    lab.add_literature_card(p.key,card,spec)
                    st.success('研究卡已保存；算法仍处于候选状态，不会自动发布。')
                    st.json(card)
                except Exception as exc:st.error(f'分析失败：{str(exc)[:200]}')
    cards=lab.literature_cards(limit=10)
    if cards:
        st.dataframe(pd.DataFrame([{'论文':c['paper_key'],'模型':c['analyst_model'],
            '研究想法':c['card'].get('testable_idea',''),'候选指纹':c['proposed_hypothesis']} for c in cards]),
            hide_index=True,use_container_width=True)
    if hyps:
        df=pd.DataFrame([{'id':x['fingerprint'],'status':x['status'],
                    'sources':x['sources'], **x['specification']} for x in hyps])
        st.dataframe(df,hide_index=True,use_container_width=True)

    st.subheader('③ 官方历史数据与实验')
    uploaded=st.file_uploader('导入从中国体彩官方公告核验的历史CSV（period,number）',type='csv',key='ar_v05')
    source=st.text_input('官方来源链接或核验说明（必填）',value='',placeholder='https://www.lottery.gov.cn/...')
    if uploaded is not None:
        try:
            source_ok=source.startswith('https://') or source.startswith('official:')
            if not source_ok:st.info('请填写官方开奖公告URL或以official:开头的核验说明。')
            data=load_csv(uploaded.getvalue())
            if any('补零' in w for w in data.warnings):st.error('请先修复前导零缺失再用于实验。')
            else:
                history=data.frame['number'].tolist()
                st.caption(f'读取{len(history)}期；数据文件SHA256：{hashlib.sha256(uploaded.getvalue()).hexdigest()[:20]}…')
                opts=[x for x in hyps if x['status'] in ('candidate','shadow')]
                select=st.multiselect('选择假设（最多8种）',[x['fingerprint'] for x in opts],max_selections=8)
                by_id={x['fingerprint']:x for x in opts}
                if st.button('开始逐期开发集回测',disabled=not(source_ok and select)):
                    if len(history)<55:st.error('至少需要55期才能启动最小实验。')
                    else:
                        result=[]
                        for fid in select:
                            h=Hypothesis(**by_id[fid]['specification'])
                            rep=walk_forward(history,h,k=100,eval_size=40)
                            lab.record_trial(fid,'development',hashlib.sha256(uploaded.getvalue()).hexdigest(),rep)
                            result.append({'hypothesis':fid,**rep})
                        st.dataframe(pd.DataFrame(result),hide_index=True,use_container_width=True)
                        st.info('开发集回测可重复试验，但反复选优会过拟合；须以后续新期号做真正独立的前向验证。')
                st.subheader('④ 生成不超过100注的研究候选集')
                k=st.number_input('注数上限',min_value=1,max_value=100,value=100)
                shadow=[x for x in hyps if x['status']=='shadow']
                st.caption('默认只使用明确标记为shadow的规则；没有活跃规则时输出可复现随机基线。')
                if st.button('计算实验候选号码',disabled=not source_ok):
                    specs=[Hypothesis(**x['specification']) for x in shadow]
                    nums,evidence=rank_100(history,specs,k=int(k))
                    st.dataframe(pd.DataFrame({'rank':range(1,len(nums)+1),'number':nums}),hide_index=True)
                    st.download_button('下载候选集CSV',
                        ('rank,number,status\n'+''.join(f'{i},{x},research_only\n' for i,x in enumerate(nums,1))).encode('utf-8-sig'),
                        'PL5_V05_100注实验候选.csv','text/csv')
                    st.json(evidence)
                st.subheader('⑤ 下一期100注封存（正式前向验证）')
                target=st.text_input('填写尚未开奖的下一期期号',placeholder='例如 2026301')
                if st.button('封存此期候选集（不可修改）',disabled=not(source_ok and target)):
                    import json
                    specs=[Hypothesis(**x['specification']) for x in shadow]
                    nums,ev=rank_100(history,specs,k=int(k))
                    rule_hash=hashlib.sha256(json.dumps([x.fingerprint() for x in specs],sort_keys=True).encode()).hexdigest()
                    result=precommit(lab.db,target_period=target,
                        previous_period=str(data.frame['period'].iloc[-1]),candidates=nums,
                        history_sha256=hashlib.sha256(uploaded.getvalue()).hexdigest(),
                        algorithm_sha256=rule_hash,source_description=source)
                    st.success('本地预注册成功；请在开奖后导入新增官方数据执行settle核验。')
                    st.json(result)
        except (ValueError,KeyError,FileNotFoundError) as exc:st.error(str(exc))

    st.subheader('⑥ 前向验证与10期滚动报告')
    prospective=outcome_report(lab.db)
    cols=st.columns(3)
    cols[0].metric('已封存期数',prospective['total_predictions'])
    cols[1].metric('已核验期数',prospective['observed_periods'])
    cols[2].metric('前向命中期数',prospective['observed_hits'])
    st.caption('开奖后可通过 research_cli.py settle --csv ... --official-source ... 更新核验。此处只展示已入库且已核验结果。')
    if prospective['rolling_10_period_windows']:
        st.dataframe(pd.DataFrame(prospective['rolling_10_period_windows'][-30:]),hide_index=True,use_container_width=True)
    st.subheader('⑦ 研究档案与状态')
    if trials:
        st.dataframe(pd.DataFrame([{'hypothesis':x['hypothesis'],'time':x['time'],
                             'hits':x['report'].get('hits'),'tested':x['report'].get('n'),
                             'phase':x['phase']} for x in trials]),hide_index=True,use_container_width=True)
    st.caption('影子规则启用请在终端执行 research_cli.py shadow --fingerprint 具体指纹；不提供自动正式发布入口。')
