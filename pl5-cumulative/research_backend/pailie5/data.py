"""读取开奖数据：保留前导零，保持开奖期序，阻止无效输入。"""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
import re
import pandas as pd

@dataclass(frozen=True)
class Draws:
    frame: pd.DataFrame
    warnings: tuple[str, ...]
    is_demo: bool = False


def load_csv(content: bytes, *, is_demo: bool = False) -> Draws:
    if not content:
        raise ValueError('文件为空。')
    errors = []
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            raw = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            errors.append(str(exc))
        except pd.errors.ParserError as exc:
            raise ValueError(f'CSV 格式错误：{exc}') from exc
    else:
        raise ValueError('CSV 编码不可识别，请转为 UTF-8。')
    aliases = {
        '期号': 'period', '开奖期号': 'period', 'issue': 'period', 'period': 'period',
        '开奖号码': 'number', '号码': 'number', 'result': 'number', 'number': 'number'
    }
    raw.columns = [aliases.get(str(c).strip().lower(), str(c).strip().lower()) for c in raw.columns]
    if not {'period', 'number'} <= set(raw.columns):
        raise ValueError('必须包含 period,number 两列（也支持“期号,开奖号码”）。')
    raw = raw[['period', 'number']].copy()
    raw['period'] = raw['period'].astype(str).str.strip()
    raw['number'] = raw['number'].astype(str).str.strip()
    if raw.empty:
        raise ValueError('无开奖记录。')
    bad_p = raw['period'].eq('')
    if bad_p.any():
        raise ValueError(f'发现 {int(bad_p.sum())} 条空期号。')
    if raw['period'].duplicated().any():
        dup = raw.loc[raw['period'].duplicated(), 'period'].iloc[0]
        raise ValueError(f'存在重复期号 {dup}，请先排查重复记录。')
    valid = raw['number'].map(lambda x: re.fullmatch(r'[0-9]{1,5}', x) is not None)
    if not valid.all():
        badidx = int(valid[~valid].index[0]) + 2
        raise ValueError(f'第 {badidx} 行号码不合法：必须是0—9组成的1至5位数字；不能含空格或分隔符。')
    warnings = []
    padded = raw['number'].str.len().lt(5).sum()
    if padded:
        warnings.append(f'{padded} 条号码少于5位，已左补零；请核对源文件是否丢失前导零。')
    raw['number'] = raw['number'].str.zfill(5)
    if raw['period'].str.fullmatch(r'[0-9]+').all():
        nums = raw['period'].map(int)
        if nums.duplicated().any():
            raise ValueError('不同期号转换为数字后重复（如 001 和 1），请规范期号。')
        if not nums.is_monotonic_increasing:
            warnings.append('数据已按数值期号从早到晚重新排序。')
        raw['_period_numeric'] = nums
        raw = raw.sort_values('_period_numeric').drop(columns='_period_numeric')
    else:
        warnings.append('期号包含非数字字符，按 CSV 原始行顺序视为时间先后，请确认已从旧到新排序。')
    raw = raw.reset_index(drop=True)
    if is_demo:
        warnings.insert(0, '当前是伪随机生成的演示数据，不是真实开奖记录；所有结果仅用于验证软件流程。')
    return Draws(raw, tuple(warnings), is_demo=is_demo)
