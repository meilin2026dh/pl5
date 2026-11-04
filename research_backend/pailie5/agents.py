"""六角色任务编排：确定性、可审计的MVP；尚未接入大语言模型。"""
from __future__ import annotations
from dataclasses import dataclass
from .data import Draws
from .engine import select_numbers, formatted_numbers
from .backtest import run_backtest, Backtest

@dataclass
class ResearchReport:
    proposals: list[str]
    backtest: Backtest
    candidate_numbers: list[str]
    gate: dict
    audit: list[str]


class ResearchWorkflow:
    """职责分离的可运行工作流，不将角色命名等同于LLM自主性。"""
    def __init__(self, data: Draws):
        self.data = data

    def run(self, *, count: int = 1000, model: str = 'ensemble', test_size: int = 80,
            window: int = 500, min_train: int = 100, seed: int = 42, use_gate: bool = True) -> ResearchReport:
        # 01 Data Agent：验证数据质量。
        if len(self.data.frame) < min_train+1:
            raise ValueError('数据不足，无法按当前参数执行滚动回测。')
        # 02 Hypothesis Agent：提出预先定义、可复现的候选假设。
        proposals = [
            'H0：各位置0至9均匀分布，号码独立均匀；任何固定K注候选集覆盖率为K/100000',
            'H1：各位数字边际分布存在稳定的非均匀性',
            'H2：不同位置之间存在稳定的非独立结构',
            '注意：H1/H2成立也不自动意味着样本外候选集优于随机对照'
        ]
        # 03 Experiment Agent：滚动回测，严格禁止数据泄漏。
        bt = run_backtest(self.data, count=count, test_size=test_size, window=window,
                          min_train=min_train, models=('positional','pairwise','ensemble'),
                          seed=seed, use_gate=use_gate)
        # 04 Filter Agent：只用全部已知期数生成“下一期”候选集。
        history = self.data.frame['number'].iloc[-window:].tolist()
        selected = select_numbers(history, count=count, model=model, seed=seed,
                                  use_gate=use_gate)
        # 05 Audit Agent：查证、明确限制。
        audit = list(self.data.warnings) + bt.warnings
        if selected.gated_fallback:
            audit.append('证据门控未支持启用所选模型；候选集合已使用同注数随机选样。')
        audit.append('未进行任何自动投注、支付或开奖预测保证。')
        # 06 Evolution Agent (MVP)：提供实验及证据供人工决定保留/淘汰模型；不自动改写可执行代码。
        audit.append('进化智能体MVP仅保存可复现的实验依据，不会自行改写算法。')
        return ResearchReport(proposals, bt, formatted_numbers(selected.numbers), selected.gate, audit)
