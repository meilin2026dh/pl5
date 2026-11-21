# PL5 V3.7.28 — GitHub 未上传文件审计报告

审计对象：本地 `PL5_V3728_Research_Full.zip` 与 GitHub `meilin2026dh/pl5` 的 `main` 分支（`pl5-cumulative/` 子目录）。

## 一、结论

- 累计包：**6,400 个文件**。
- GitHub `main`：**1,186 个文件**，包含 `pl5-cumulative/` **910 个**及原 Web 项目 **276 个**。
- 累计包中与已同步路径匹配的文件：**910**。
- **未上传：5,490 个文件**，原始内容约 **71.14 MiB**（74,597,479 字节）。
- 缺失文件的扩展名不包括 `.py/.js/.ts/.tsx/.ps1/.sh/.bat` 等常规源程序；这意味着本次未同步的主体是科研结果、数据、版本清单，而不是常规程序源码。**JSON 数学表达、参数、规则仍可能构成有价值的科研资产。**
- GitHub 原有的 276 个文件主要是 Web 项目及其 docs/，仅 `.gitignore`、`README.md` 与累计包同名，而这两项已经存在于 `pl5-cumulative/` 已同步清单中，故不能将276个原项目文件从累计包缺口中扣除。

**纠正统计口径：** `6,400−1,186=5,214` 只是不同文件集合的数量相减，**不是实际缺失文件数**。

## 二、按文件类别汇总

| 类别 | 未上传数量 | 未上传原始字节 | 建议 |
|---|---:|---:|---|
| 运行与实验输出 | 3,933 | 7,822,713 | 优先归档科研证据，不必一律进源码主分支 |
| 研究资料与实验文档 | 1,467 | 21,704,819 | 优先归档科研证据，不必一律进源码主分支 |
| 版本清单及根目录记录 | 44 | 10,301,982 | 逐项审查再分类上传 |
| 合成与示例数据 | 35 | 21,986,986 | 逐项审查再分类上传 |
| 后端运行数据与样本 | 8 | 12,778,821 | 逐项审查再分类上传 |
| 开奖转录数据与溯源 | 3 | 2,158 | 逐项审查再分类上传 |

## 三、值得优先处理的遗漏

**（1）版本与校验清单**：根目录有44个发布、SHA256和回归文件未上传。其中包括 `PL5_V3728_MANIFEST.json` 与 `PL5_V3728_PATCH_MANIFEST.json`。此外此前交付的“源码整理包”实际含912项，比当前GitHub的910项多两项：`PL5_V3727_MANIFEST.json` 和 `PL5_V3728_MANIFEST.json`。

**（2）后端演示数据**： `research_backend/` 还有8个文件未上传，主要是合成 CSV、100,000 注演示表和1个SQLite运行库。不是常规代码文件。

**（3）官方开奖转录**：`data/official_transcriptions_v3719/` 3个文件未同步，需要核对出处、许可与数据准确性。

**（4）研究报告与实验证据**：`docs/v373/` 有1,241个文件、`runs/v3726/` 有1,368个文件没有上传。这些数量大、可能包含重复运行输出，应有版本化归档策略。

**（5）私有盲测材料**：文件名含 `/private/` 或 `developer_known.json` 的资料应保留在私有受控存储，不宜直接提交到公开 GitHub；出现 sqlite/官方转录的也需审查。当前根据**文件名/路径**提示需审查的文件有 {len(flagged)} 个；并未对每个 JSON 的内部内容做全面敏感信息扫描，所以此数不能代表全部风险。

## 四、代表性未上传路径

版本元数据：

- `PL5_V3714_RELEASE_MANIFEST.json`
- `PL5_V3719_MANIFEST.json`
- `PL5_V3719_PHASE2_MANIFEST.json`
- `PL5_V3719_PHASE3_MANIFEST.json`
- `PL5_V3720_MANIFEST.json`
- `PL5_V3721_MANIFEST.json`
- `PL5_V3722_MANIFEST.json`
- `PL5_V3723_MANIFEST.json`
- `PL5_V3723_Package_Audit.json`
- `PL5_V3724_MANIFEST.json`
- `PL5_V3725_MANIFEST.json`
- `PL5_V3726_MANIFEST.json`

后端样本：

- `research_backend/data/synthetic_demo.csv`
- `research_backend/examples/pattern_demo_candidates.csv`
- `research_backend/examples/v03_demo_all_rank.csv`
- `research_backend/examples/v06_unapproved_baseline_top100.csv`
- `research_backend/examples/v11_synthetic_demo/all_100000.csv`
- `research_backend/examples/v11_synthetic_demo/top_k.csv`
- `research_backend/examples/v18_demo_history.csv`
- `research_backend/runtime/v34_parameter_audit.sqlite`

V3.7.28 当前研究数据示例：

- `docs/v3728/REGRESSION_SUMMARY.json`
- `docs/v3728/group_01.log`
- `docs/v3728/group_02.log`
- `docs/v3728/group_03.log`
- `docs/v3728/group_04.log`
- `docs/v3728/group_05.log`
- `docs/v3728/group_06.log`
- `docs/v3728/group_07.log`
- `docs/v3728/group_08.log`
- `docs/v3728/group_09.log`

## 五、核验方法与边界

1. 读取本地官方交付 ZIP 的6400个非目录条目，逐一记录文件路径、大小和内容SHA256。
2. 从 GitHub 连接器获取 `main` 的完整递归树（`truncated=false`），得到 `pl5-cumulative/` 下910个文件。
3. 对连接器读取的910条路径按UTF-16代码单元排序计算FNV32，结果 `227bb769`；与此前逐文件校验后的本地同步索引一致。
4. 在相同相对路径口径下进行集合差集，得到5490个路径。原 Web 项目中的路径不补充这些缺口。
5. 这里只证明**文件路径存在/缺失**；已有文件的全量内容一致性本次没有重算；也不代表 V1.x 至 V3.7.28 的每一份历史独立快照都在累计包里。

## 六、建议后续实施顺序

- **P0：** 补全少量版本 `MANIFEST`、`SHA256SUMS` 和关键溯源文件（上传前检查是否有敏感内容）。
- **P1：** 对 `docs/` 中有科研价值的可复现实验设计、原始数据和验证报告，按版本分类入库，避免被日志淹没。
- **P2：** 将 `runs/`、大规模CSV和JSON输出存成 GitHub Releases、受控证据库或对象存储，并附哈希索引；不要简单把3,933个运行输出塞入 `main` 源码树。
- **保密审查：** 含私有任务答案的文件只放私有仓库/受控存储。公开仓库中不应出现密钥、私有盲测答案或身份信息。

## 七、交付文件

- `PL5_V3728_GitHub_Missing_5490.csv`：5,490条完整路径、大小、SHA256、分类、建议动作和需审查标记。
- `PL5_V3728_GitHub_Missing_ByFolder.csv`：按文件夹汇总，用于找出数据膨胀源。
- `PL5_V3728_GitHub_Upload_Priority.csv`：高优先级缺口及需审查文件。
- `PL5_V3728_GitHub_Missing_Audit_Evidence.json`：包哈希、比较方法和审计摘要。