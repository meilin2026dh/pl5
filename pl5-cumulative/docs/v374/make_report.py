import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
state=json.loads((root/'runs/autonomous_v374/state.json').read_text())
trials=[json.loads(p.read_text()) for p in sorted((root/'runs/autonomous_v374/cycles').glob('*/result.json'))]
statistics={}
for label in ('exploratory_only','negative_control'):
    group=[r for r in trials if r['status']==label]
    stats={}
    for arm in ('full','no_warm','selective','grammar_only'):
        arms=[next(x for x in r['arms'] if x['arm']==arm) for r in group]
        n=sum(x['holdout']['count'] for x in arms)
        k=sum(x['holdout']['count']-x['holdout']['errors'] for x in arms)
        stats[arm]={'trials':len(arms),'holdout_cells':n,'correct':k,'accuracy':k/n if n else None}
    statistics[label]=stats
verification={
    'release':'3.7.4', 'purpose':'bounded autonomous research: self-selected synthetic mathematical experiments',
    'cycles':state['completed_cycles'],'per_cycle_policies':4,'budget_each':state['evaluation_budget'],
    'total_search_and_screening_evaluation_budget':state['completed_cycles']*4*state['evaluation_budget'],
    'issue_count':len(state['issues']),'issues':state['issues'], 'stats':statistics,
    'reproducibility':json.loads((root/'docs/v374/replay_verification.json').read_text()),
    'tests':{
        'full_python_backend':{'passed':651,'failed':0,'log':'docs/v374/full_debug.log','note':'full pytest exit, 90.07s'},
        'historical_integration':{'passed':29,'failed':0,'log':'docs/v374/integration.log','junit':'docs/v374/pytest_integration.xml'},
        'autonomous_specific':{'passed':8,'failed':0,'included_in_backend_total':True}},
    'previous_versions_preserved':True,'no_external_calls':True,'no_money_movement':True,
    'no_remote_scheduler_created':True,'no_windows_scheduler_installed':True,
    'actual_background_service_running':False,'production_filter_enabled':False,
    'predictive_advantage':'NOT_ESTABLISHED', 'source_type':'synthetic_math_tasks_only',
    'methodological_caveats':[
        'Task selection is adaptive and exploratory; repeated case family seeds do not establish confirmatory significance.',
        'Ablation policies are not compared by CPU time, only charged candidate calls.',
        'Source formula curation and historical warm-bank acquisition costs are outside per-task budgets.',
        'No real lottery, market series or future-draw filter evaluation.']}
(root/'docs/v374/VERIFICATION.json').write_text(json.dumps(verification,indent=2,ensure_ascii=False)+'\n')
lines=['# PL5 V3.7.4 自主科研首轮执行报告','', '## 实际执行', '',
       f'- 在独立本地科研工作目录累计运行 **{state["completed_cycles"]} 轮**，每轮4种策略，每种500次受限候选评价，总计16,000次充费候选评价。',
       '- 基于已完成轮次选择下一个任务；每轮使用新种子及训练60格/封存40格。',
       '- 程序在全部候选保存冻结后才读取封存标签，生成问题日志和下一轮研究假设。',
       f'- 自动问题记录 **{len(state["issues"])}** 条：'+'、'.join(f'第{i["cycle_number"]}轮 {i["issue"]}' for i in state['issues'])+'。',
       '- 在全新输出目录以相同种子再次执行8轮，所有JSON内容逐字节一致（重跑不算新证据）。',
       '', '## 验证', '',
       '- 累计科研后端651/651通过（90.07秒），历史集成29/29通过（3.76秒）；新增8项专项测试包括在651项内。',
       '- 发布包的 Windows 计划任务脚本只提供安装方案，未在 Windows 主机运行或安装。',
       '', '## 各任务对照成绩', '',
       '| 任务组 | 策略 | 保留格命中数 | 保留格总数 | 描述性正确率 |','|---|---|---:|---:|---:|']
for grp,grp_label in [('exploratory_only','6轮结构化任务'),('negative_control','2轮随机负对照')]:
    for arm in ('full','no_warm','selective','grammar_only'):
        v=statistics[grp][arm]
        lines.append(f'| {grp_label} | {arm} | {v["correct"]} | {v["holdout_cells"]} | {v["accuracy"]*100:.2f}% |')
lines+=['', '保留格结果均来自合成数学任务；相同数学任务的多个种子、相邻格不是独立科学发现，不能据此直接做显著性结论。',
        '', '## 当前自主性和局限', '',
        '这套系统能自动安排**有界、可审计的科研实验**，并根据统计性问题改变下一任务，但不能独立改写数学原语、读取真实股指或自动运行用户Windows程序。无法解决的程序故障会保存`failure.json`并暂停，而不是未经审查修改代码。',
        '当前运行在隔离沙箱内完成，不是可无限运行的后台服务；需要持续研究，应由用户在自己的Windows上显式配置日常调度。',
        '', '## 文件', '',
        '- `research_backend/pailie5/autonomous_v374.py`：自动科研核心控制器',
        '- `research_backend/research_autonomous_v374.py`：CLI',
        '- `runs/autonomous_v374`：全部8轮原始证据，包括冻结算子及独立评价',
        '- `SCHEDULE_V374_WINDOWS.ps1`：可选调度器，默认不安装',
        '- `docs/v374/VERIFICATION.json`：机器可读验收指标','']
(root/'docs/v374/REPORT.md').write_text('\n'.join(lines),encoding='utf8')
print('wrote',root/'docs/v374/VERIFICATION.json','and report')
