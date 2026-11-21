# PL5 V3.7.19 Phase III — 官方历史数据摘录、滚动回测与公开摘要封存

## 1. 现有可信度

- 记录来源：江苏省体育彩票管理中心（走势表26244—26293期、26294期公告）、甘肃省体育彩票管理中心（26275—26294期历史数据）。
- 从公开网页文字记录人工摘录，江苏 **51** 期、甘肃 **20** 期；其中 **20** 期号码逐项一致、另有 **31** 期江苏记录未完成第二来源交叉验证。
- 没有取得来源站点 HTML 原始字节、HTTP 响应头、网站数字签名或第三方采集归档，**不得宣称已独立认证所有记录**。
- 数据目录 `data/official_transcriptions_v3719/`，来源和局限性见 `PROVENANCE.json`。

## 2. 第一轮真实历史回测

训练/评估：总51期，前40期预热，最后11期（26284—26294）作为回顾性滚动窗口。每期每策略从10万注中输出100注，采用固定种子3719。全部11期结果都出现在双源重叠区间；31条未交叉验证记录仍可能出现在训练前缀。

| 方法 | 命中 | 单侧二项检验p值 |
|---|---:|---:|
| random | 0 / 11 | 1.0000 |
| positional | 0 / 11 | 1.0000 |
| pairwise | 0 / 11 | 1.0000 |
| ensemble | 0 / 11 | 1.0000 |
| heuristic_rank | 0 / 11 | 1.0000 |

每期独立公平开奖、每策略100注的零假设命中概率是0.001。这只是事后滚动回测，不是开奖前成功预测；11期不足以判断统计优势。本次**没有观察到命中，也没有证实预测优势**。

## 3. 26295期研究摘要公开封存

- 本地研究登记：`runs/v3719/phase3/26295_registration.json`
- 本地完整候选封存：`runs/v3719/phase3/26295_seal.json`
- 本地开放式RFC3161时间戳请求：`runs/v3719/phase3/26295_seal.tsq`（**不是TSA回执**）。
- GitHub摘要公开：https://github.com/meilin2026dh/pl5/pull/4 （草稿PR，未合并，独立于主分支）。
- GitHub记录PR创建时间：**2026-11-04T23:18:41Z / 北京时间2026-11-05 07:18:41**。
- seal文档SHA-256：`ee65f6bff6a76faaa40019647f7fd42dbe3b38f3fef655d430127cb4c76835e4`
- 封存JSON文件字节SHA-256：`58ea4865e6410da6c2e32a04ae17155a287c37b651bb967c7453ca35e7ea67cb`
- 摘要提交 commit：`c4edaabb874a225db065f7fb346a5c10c9ab0c43`
- 根据官方2022年调整公告，排列5常规每日开奖时间为北京时间21:25；本次GitHub摘要记录早于2026-11-05的常规开奖时间。请独立核对实际开奖事件及官方特殊调整。

GitHub PR创建时间属于外部服务记录，**不是RFC3161签名时间戳**；且缺少独立的官方当期开奖时间证明，暂不将该实验标记为“具完整第三方时间证明的正式预测能力验证”。

## 4. Linux / Windows 安装后运行

工程目录（示例）：`D:\pl5`。建议先单独解压本完整包，不覆盖其他实验目录。

```powershell
cd D:\pl5
py -3.12 -m pip install -e .\research_backend pytest
py -3.12 -m pytest -q research_backend\tests\test_official_dataset_v3719.py
py -3.12 research_backend\research_official_v3719.py inspect --primary data\official_transcriptions_v3719\jiangsu_transcribed.csv --witness data\official_transcriptions_v3719\gansu_transcribed.csv --primary-url https://www.js-lottery.com/Chart/p5Number --witness-url https://www.gstc.org.cn/wanfa/pl5_history --min-overlap 20 --consecutive --out runs\v3719\phase3\my_quality_audit.json
```

同名输出采用独占创建（不得覆盖），需换新路径重复运行。未联网时程序仍可验证已有的转录CSV和哈希，但不会重新从网页下载数据。

通过RFC3161获取可信时间戳：将 `26295_seal.tsq` 送到可信的外部时间戳机构，留存 `.tsr` 与受信任CA根证书，再执行：

```powershell
py -3.12 research_backend\research_official_v3719.py timestamp-verify --packet runs\v3719\phase3\26295_seal.json --response path\receipt.tsr --trusted-ca path\tsa_roots.pem --out runs\v3719\phase3\tsa_verified.json
```

当前**未取得 .tsr 回执**，不要声称上述验证已通过。最后需要收集26295期的双源实际开奖结果后才可以运行 `settle`；在当前研究交付时尚未结算。

## 5. 验收与研究边界

- 新增13项数据质量、冲突注入及RFC3161请求测试。
- 已通过阶段III与原阶段I/II的定向测试、以及历史集成测试。完整后端结果以 `runs/v3719/phase3/all_tests_log.txt` 为准。
- 不得将GitHub摘要发布时间、程序哈希核验或者开奖历史回测，替代预测能力的统计证据。
- GitHub目前只公开了封存摘要（没有合并完整V3.7.19源码）；完整科研交付在本ZIP内。
