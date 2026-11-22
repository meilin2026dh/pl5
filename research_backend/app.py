"""Streamlit用户界面。使用：uv run streamlit run app.py"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from pailie5.data import load_csv
from pailie5.engine import MODEL_LABELS, select_numbers, formatted_numbers
from pailie5.backtest import run_backtest

st.set_page_config(page_title='排列五 | 自适应过滤实验台', page_icon='🧪', layout='wide')
st.title('排列五 · 自适应过滤实验台')
st.caption('MVP v0.1｜研究型多角色工作流｜默认离线运行，不接大模型，不提供预测保证')
st.warning('核心数学边界：公平独立开奖下，保留 K 注的理论覆盖率恒为 K/100,000。任何历史回测表现都不能保证未来中奖。')

@st.cache_data(show_spinner=False)
def parse_csv(content: bytes, demo: bool):
    return load_csv(content, is_demo=demo)

def frame_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8-sig')

with st.sidebar:
    st.header('实验设置')
    uploaded = st.file_uploader('上传真实历史开奖CSV', type=['csv'], help='列名为 period,number；每行一期，从旧到新或使用数字期号自动排序。')
    demo = uploaded is None
    count = st.number_input('保留注数 K', min_value=1, max_value=100_000, value=1000, step=100)
    window = st.number_input('训练回看窗口（期）', min_value=20, max_value=30_000, value=500, step=50)
    ntest = st.number_input('最近回测期数', min_value=1, max_value=3000, value=80, step=10)
    min_train = st.number_input('最少训练期数', min_value=20, max_value=5000, value=100, step=20)
    seed = st.number_input('随机种子', min_value=0, max_value=2_000_000_000, value=42)
    gate = st.checkbox('开启训练集证据门控（推荐）', value=True,
                       help='使用位置均匀性与位置间独立性检验；无足够证据时回退随机对照。')
    model = st.selectbox('候选集生成模型', list(MODEL_LABELS), index=2, format_func=lambda m:MODEL_LABELS[m])

if demo:
    content = (Path(__file__).parent / 'data' / 'synthetic_demo.csv').read_bytes()
else:
    content = uploaded.getvalue()
try:
    draws = parse_csv(content, demo)
except Exception as e:
    st.error(f'数据导入失败：{e}')
    st.stop()

st.info('数据源：**随机生成演示数据（非真实开奖）**' if demo else f'数据源：**{uploaded.name}**（用户上传）')
for w in draws.warnings:
    st.caption('⚠ ' + w)

first, second, third, fourth = st.tabs(['数据概览', '候选集生成', '滚动回测', '算法与审计说明'])
with first:
    a,b,c = st.columns(3)
    a.metric('导入期数', f'{len(draws.frame):,}')
    b.metric('完整号码空间', '100,000')
    c.metric('随机基线单期覆盖率', f'{count/1000:.3f}%')
    st.dataframe(draws.frame.tail(30).iloc[::-1], use_container_width=True, hide_index=True)
    st.download_button('下载CSV示例结构', b'period,number\n2026001,01234\n2026002,90876\n',
                       'csv_template.csv', mime='text/csv')

with second:
    st.subheader('生成下一期实验候选集')
    st.caption('只使用现有历史记录。下次开奖的号码未知；同一期已知数据不能拿来“预测”自身。')
    if st.button('生成候选集', type='primary', key='make'):
        hist = draws.frame['number'].iloc[-int(window):].tolist()
        result = select_numbers(hist, count=int(count), model=model, seed=int(seed), use_gate=gate)
        st.session_state['selection'] = result
        st.session_state['selection_key'] = (hash(content), int(count), int(window), int(seed), gate, model)
    current_key = (hash(content), int(count), int(window), int(seed), gate, model)
    if 'selection' in st.session_state and st.session_state.get('selection_key') == current_key:
        chosen = st.session_state['selection']
        a,b,c = st.columns(3)
        a.metric('候选注数', f'{len(chosen.numbers):,}')
        b.metric('号码压缩率', f'{100-len(chosen.numbers)/1000:.3f}%')
        c.metric('随机假设下的覆盖率', f'{len(chosen.numbers)/1000:.3f}%')
        if chosen.gated_fallback:
            st.warning('本轮已退回等注数随机选择。原因：' + chosen.gate['reason'])
        else:
            st.info('已按探索模型评分排名；统计异常不代表可预测优势。' + chosen.gate['reason'])
        st.caption('校正后p值：' + ('不适用' if chosen.gate['p_adjusted'] is None else f"{chosen.gate['p_adjusted']:.5g}"))
        nums = formatted_numbers(chosen.numbers)
        st.code('  '.join(nums[:min(80,len(nums))]) + (' …' if len(nums)>80 else ''), language=None)
        st.download_button('下载完整候选集CSV', frame_csv(pd.DataFrame({'number':nums})),
                           'candidate_numbers.csv', mime='text/csv')

with third:
    st.subheader('真正的逐期滚动样本外回测')
    st.caption('对于第 t 期，算法只能看到 t 期之前的历史记录。回测同时运行位置、双位置、融合与随机对照。')
    if st.button('开始滚动回测', type='primary', key='backtest'):
        try:
            with st.spinner('在历史期次中逐期训练、筛选和统计中…'):
                bt = run_backtest(draws, count=int(count), test_size=int(ntest), window=int(window),
                                  min_train=int(min_train), seed=int(seed), use_gate=gate)
            st.session_state['bt'] = bt
            st.session_state['bt_key'] = (hash(content), int(count),int(ntest),int(window),int(min_train),int(seed),gate)
        except Exception as e:
            st.error(str(e))
    bt_key = (hash(content), int(count),int(ntest),int(window),int(min_train),int(seed),gate)
    if 'bt' in st.session_state and st.session_state.get('bt_key') == bt_key:
        bt = st.session_state['bt']
        st.caption(f'实际回测 {bt.n_test} 期；每期候选 {bt.count} 注；公平随机期望命中期数 {bt.n_test*bt.count/100000:.2f}。')
        stats = bt.summary.copy()
        for col in ['命中率','95%置信区间下界','95%置信区间上界','退回随机比例']:
            stats[col] = stats[col].map(lambda x:f'{x*100:.2f}%')
        for col in ['单模型单侧p值','Bonferroni校正p值']:
            stats[col] = stats[col].map(lambda x:'—' if pd.isna(x) else f'{x:.5g}')
        st.dataframe(stats, hide_index=True, use_container_width=True)
        pivot = bt.rows.pivot(index='period', columns='model', values='hit').fillna(0)
        st.line_chart(pivot.cumsum(), y_label='累计命中期数')
        st.download_button('下载逐期实验明细 CSV',frame_csv(bt.rows),'walkforward_details.csv',mime='text/csv')
        st.download_button('下载回测统计 CSV',frame_csv(bt.summary),'walkforward_summary.csv',mime='text/csv')
        for msg in bt.warnings:
            st.caption('• ' + msg)
        evidence = bt.summary.loc[(bt.summary['模型'] != 'random') &
                                  (bt.summary['Bonferroni校正p值'].fillna(1) < 0.01)]
        if evidence.empty:
            st.info('本次未得到通过当前校正阈值（0.01）的优于随机基线证据。')
        else:
            st.warning('部分探索性测试出现低p值，但反复调参及多次尝试仍需进一步校正；不能据此认定存在可持续预测优势。')

with fourth:
    st.markdown('''
**六个功能角色（MVP不调用语言模型）：**

1. 数据角色：期号、前导零、重复与顺序检查。
2. 假设角色：生成可检验的位置均匀性和位置独立性研究假设。
3. 实验角色：训练历史窗口、逐期预测下一期、记录实验指标。
4. 过滤角色：用概率评分排名输出精确 K 注候选集。
5. 审计角色：训练集多重检验、样本量门控、不确定性与随机基线对照。
6. 进化角色：为后续模型淘汰/加入新算法保留可复现的报告接口（尚不自动修改代码）。

**算法局限：** 位置模型采用拉普拉斯平滑；双位置模型计算10组联合频率；融合模型把两个分数标准化后平均。它们都是探索性排序器，**输出分数不是中奖概率**。默认开启证据门控，没有训练集统计证据时使用均匀随机对照。门控的异常检测不等价于能预测未来。

**实验设计：** 测试集按时间排列；不允许用测试期真实号码参与当期筛选。二项分布p值以公平独立开奖为前提，Bonferroni校正只覆盖本轮展示的模型数，并未覆盖反复挑选参数、反复查看结果等研究者自由度。

**安全与成本：** 系统不接支付、不自动购买彩票，不声称任何保本或中奖保证。当前版本不自动访问第三方开奖接口，真实数据由用户自行提供CSV。
''')
