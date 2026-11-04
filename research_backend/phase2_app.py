"""V0.2浏览器工作台：uv run streamlit run phase2_app.py。"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from pailie5.knowledge import KnowledgeBase, fingerprint, holdout_key
from pailie5.data import load_csv
from pailie5.research_agent import ResearchAgent

ROOT=Path(__file__).parent
DB=ROOT/'runtime'/'knowledge.sqlite'
st.set_page_config(page_title='排列五 · 算法科学家 V0.2',page_icon='🧪',layout='wide')
st.title('排列五 · 算法科学家实验室')
st.caption('V0.2  |  数据来源审计 · 算法受限生成 · LangGraph工作流 · 独立封存测试集 · SQLite知识库')
st.warning('研究工具，不是彩票预测或投注程序。公平开奖时，K注的理论命中概率固定为 K/100,000。')
with st.sidebar:
    st.header('实验参数')
    use_demo=st.toggle('运行合成演示数据',value=True,help='默认演示数据来自伪随机生成；真实数据请先导入下方知识库')
    count=st.number_input('每期候选注数 K',1,100_000,1000,step=100)
    dev_size=st.number_input('开发期数',10,1000,40,step=10)
    holdout_size=st.number_input('封存期数',10,1000,40,step=10)
    min_train=st.number_input('最少训练期数',20,5000,100,step=20)
    window=st.number_input('滚动窗口',20,20000,500,step=50)
    seed=st.number_input('随机种子',0,2_000_000_000,42)
    mode=st.selectbox('工作流引擎',['auto','off','required'],help='auto有LangGraph时使用图执行，否则走同构确定性流程；required未安装会报错')
    llm=st.checkbox('允许调用OpenAI提出受限假设（可选）',value=False,
                    help='需要用户在本机环境变量配置OPENAI_API_KEY，可能产生API费用；不会执行LLM给出的代码')

kb=KnowledgeBase(DB)
try:
    tabs=st.tabs(['数据入库','自主研究','算法知识库','复现与说明'])
    with tabs[0]:
        st.subheader('真实开奖记录导入与来源追溯')
        st.write('推荐从中国体彩网公开历史开奖页面获取记录并整理CSV。**系统无法仅凭文件名判断其是否为官方真数据**，请保留出处供人工核验。')
        uploaded=st.file_uploader('选择开奖CSV（期号period、5位number）',type=['csv'])
        source=st.text_input('来源说明（例如：某官方网页人工核对导出+获取日期）')
        if uploaded is not None:
            try:
                incoming=load_csv(uploaded.getvalue())
                st.caption(f'待导入 {len(incoming.frame)} 条 · 文件SHA256: {hashlib.sha256(uploaded.getvalue()).hexdigest()[:20]}…')
                st.dataframe(incoming.frame.tail(12),hide_index=True,use_container_width=True)
                for warning in incoming.warnings:st.warning(warning)
            except Exception as exc:
                st.error(f'预检失败：{exc}')
        if st.button('严格校验并写入SQLite',type='primary',disabled=uploaded is None or not source.strip()):
            try:
                rec=kb.import_csv(uploaded.getvalue(),source.strip())
                st.success(f'{rec.status}：共{rec.records}条，新增{rec.inserted}条，来源编号{rec.source_id}')
            except Exception as exc:
                st.error(str(exc))
        st.divider()
        st.write('**已登记数据源**')
        sources=kb.sources()
        if sources:
            cols=['id','name','kind','rows','first_period','last_period','sha256','imported_at']
            st.dataframe(pd.DataFrame(sources)[cols],hide_index=True,use_container_width=True)
        else: st.info('尚未导入真实开奖记录。')
        st.download_button('下载CSV结构样例',
                           'period,number\n2026001,01234\n2026002,90876\n'.encode('utf-8-sig'),
                           '数据结构样例_仅示意.csv',mime='text/csv')
    with tabs[1]:
        st.subheader('自动提出假设 → 开发集竞争 → 预注册 → 封存验证')
        if use_demo:
            draws=load_csv((ROOT/'data'/'synthetic_demo.csv').read_bytes(),is_demo=True)
            st.info('当前运行：伪随机演示数据，不代表真实开奖结果。')
        else:
            try:
                draws=kb.merged_draws()
                st.success(f'已从真实数据知识库载入{len(draws.frame)}条**声称来源的**开奖记录；仍需人工核对公告真实性。')
            except ValueError as exc:
                draws=None
                st.warning(str(exc))
        if draws is not None:
            st.caption(f'数据指纹：{fingerprint(draws)[:24]}… · 当前记录 {len(draws.frame)} 期')
            a,b,c=st.columns(3)
            a.metric('开发集（期）',str(dev_size))
            b.metric('封存集（期）',str(holdout_size))
            c.metric('均匀随机理论覆盖率',f'{count/1000:.3f}%')
            try:
                key=holdout_key(draws,int(holdout_size))
                existing=kb.get_experiment(key)
                if existing:
                    st.warning(f'这个数据集的同一封存测试集已被开封或锁定（实验 #{existing["id"]}）。请导入新的后续开奖数据后再开展下一轮独立检验。')
            except ValueError:
                existing=None
            if st.button('启动研究智能体',type='primary',disabled=existing is not None):
                try:
                    with st.spinner('正在进行开发集回测、预注册与一次性封存测试…'):
                        report=ResearchAgent(draws,kb).run(count=int(count),dev_size=int(dev_size),
                            holdout_size=int(holdout_size),min_train=int(min_train),window=int(window),
                            seed=int(seed),llm=llm,use_langgraph=mode)
                        st.session_state['last_phase2_report']=report
                    st.success(f'实验 #{report["experiment_id"]} 结束；结论状态：{report["holdout"]["status"]}')
                except Exception as exc:
                    st.error(f'实验中止：{exc}')
            result=st.session_state.get('last_phase2_report')
            if result and result['dataset_sha256']==fingerprint(draws):
                st.write('**开发集实验比较**')
                dev=pd.DataFrame([{
                    '假设':r['name'], 'log概率增益':round(r['metrics']['mean_log_gain'],6),
                    '开发集命中数':r['metrics']['hits'], '校正p值':round(r['p_adjusted'],6),
                    '决策':r['decision']} for r in result['development']])
                st.dataframe(dev,hide_index=True,use_container_width=True)
                st.write('**封存集一次性验收**')
                h=result['holdout']
                st.json(h,expanded=True)
                st.download_button('下载实验全量报告(JSON)',json.dumps(result,ensure_ascii=False,indent=2).encode('utf8'),
                                   'V02实验报告.json',mime='application/json')
    with tabs[2]:
        st.subheader('已预注册的实验与模型知识')
        rows=kb.experiments()
        if rows:
            frame=pd.DataFrame(rows)
            st.dataframe(frame[['id','registered_at','dataset_fingerprint','status']],hide_index=True,use_container_width=True)
            which=st.selectbox('查看实验',frame['id'].tolist())
            run=next(row for row in rows if row['id']==which)
            st.json({'preregistration':json.loads(run['preregistration']),
                     'development':json.loads(run['dev_result']),
                     'holdout':json.loads(run['holdout_result'])},expanded=False)
        else: st.info('暂无已注册实验。')
    with tabs[3]:
        st.markdown('''
        #### 研究边界
        - 自动提案依赖确定性算法模板。若配置API Key，可以使用语言模型生成**受限制的JSON假设**，不执行任何LLM产生的源代码。
        - 使用LangGraph时，将6个研究节点串联并写入SQLite检查点；未安装时使用同一逻辑的本地顺序执行模式。
        - 真实数据采取严格5位校验，记录文件SHA256，跨来源冲突直接阻断，不会覆盖。
        - 在任何封存集查询前，系统已经保存开发集筛选结论；同一数据指纹和封存区间仅允许一次正式检验。
        - 算法不能可靠超过随机基线时，不会宣称预测优势。任何历史异常都不意味着可以重复利用。
        - 此实验台不提供自动购买、投注接口或中奖保证。

        #### 推荐入口
        ```bash
        uv sync --extra agent
        uv run streamlit run phase2_app.py
        uv run python agent_cli.py --help
        ```
        ''')
finally:
    kb.close()
