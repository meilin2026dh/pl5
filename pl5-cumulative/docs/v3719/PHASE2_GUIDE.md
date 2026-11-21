# PL5 V3.7.19 第二阶段：双来源核验、预注册、开奖前本地封存与开奖后结算

本模块新增 `research_backend/pailie5/prospective_validation_v3719.py`、CLI、20 项独立安全测试。

**重要：本地文件创建时间和 SHA256 并不能由系统自身证明文件是在开奖前生成。** 如果要获得更可靠的前向研究证据，应在开奖前把封存包的完整 SHA256 摘要通过 GitHub 公共提交、第三方可信时间戳或其他独立审计渠道发布，并保存第三方返回的时间证明。此版本不验证第三方证明，也不自动联网抓取或下注。

## 1. 准备数据

分别从两个**你已人工确认来源**的机构渠道保存 CSV，要求：

```csv
issue,number
26291,27624
26292,44610
26293,81146
26294,32938
```

这些示例开奖号码可以用官方公告核对，但只有 4 条，不满足不少于 40 条的实际候选构建要求。必须自行获得足够的完整、可信、从早到晚排序的数据，不得把示例当作官方全量数据库。

第二份文件格式相同，表头可以改为 `period,number`。两份 CSV 不能是完全相同的原文件副本。系统会对所有重复期号逐条核对，有一项冲突就拒绝执行，并记录两份原始文件的 SHA256。但两个来源可能共享上游数据，**交叉一致不等于来源已经被独立认证**。

## 2. 命令行（Python 3.12+）

从根目录运行：

```bash
python -m pip install -e ./research_backend pytest
python research_backend/research_prospective_v3719.py crosscheck \
  --primary primary.csv --witness witness.csv --out audit/crosscheck.json

python research_backend/research_prospective_v3719.py register \
  --primary primary.csv --witness witness.csv \
  --primary-url https://your-official-publishing-page.example/draws \
  --witness-url https://your-second-source.example/draws \
  --study-id pl5-forward-001 --target 26295 --warmup 40 --top-k 100 \
  --methods random positional pairwise ensemble heuristic_rank \
  --out audit/registration.json

python research_backend/research_prospective_v3719.py seal \
  --primary primary.csv --witness witness.csv \
  --registration audit/registration.json --out audit/seal.json

python research_backend/research_prospective_v3719.py verify \
  --registration audit/registration.json --packet audit/seal.json
```

注意：上述 `.example` 网址只是必须由你替换的**占位符**，不是已核验或可访问的网站。演示的 `--target` 也是示例，必须用你当时**尚未公布结果**的新一期期号。注册、封存均采用新建文件模式，不覆盖旧证据。

**开奖前**：将 `seal.json` 的 `document_sha256` 通过独立审计渠道公开或提交，保存外部回执。不要删除、修改原始 CSV、注册文件、封存文件和回执。

**开奖后**：两份 CSV 都增补目标期号的相同真实结果后执行：

```bash
python research_backend/research_prospective_v3719.py settle \
  --primary primary.csv --witness witness.csv \
  --registration audit/registration.json --packet audit/seal.json \
  --out audit/settlement.json

python research_backend/research_prospective_v3719.py verify \
  --registration audit/registration.json --packet audit/seal.json \
  --settlement audit/settlement.json
```

结算将验证历史训练前缀未改、候选包完整、两来源目标期号一致，再计算命中与否和同注数随机概率。默认每期每算法 100 注，在公平独立开奖假设下，每期随机命中概率 0.001。

## 3. 两类实验不可混淆

- **合成演示**：`runs/v3719/phase2_demo/` 的 43 条训练记录和第 44 条结果全是随机生成，两个 CSV 是同一模拟样本的不同文件表示，不构成真实的来源独立性。这仅证明程序可正确注册、封存、核验和结算。
- **真实回测**：V3.7.19 第一阶段 `research_v3719.py --csv ...` 是回溯研究，即便来源真实也不能证明预测在开奖前出现。
- **真实前向封存**：必须使用目标开奖前的真实已发表历史数据，且第三方外部时间证明早于开奖/结果公开时间，才可能支持更强的证据等级。该条件目前尚未达到。

## 4. 验收边界

- 当前模块对五个策略实现一致预算、训练历史隔离、不可覆盖存储、SHA256 内部完整性检查、双 CSV 冲突阻断、来源标识、开奖后结算。20 项新回归测试。
- 未核验第三方时间戳或原网页签名，未完成真实历史 40+ 期的双源全量数据采集，也未在目标期开奖前提交真实候选摘要；因此**不宣称前向预测效果**。
- Linux Python 3.13 已运行。Windows Python 3.12 及 `D:\pl5` 实机仍待本机执行。
