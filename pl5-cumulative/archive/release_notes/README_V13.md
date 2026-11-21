# PL5 V1.3｜五序 GitHub 源码融合 + ESSE 独立规则复核

**本次是真正包含经GitHub校验的原版源文件的升级包。** 与V1.2只提供接入补丁不同，现附带四个与 `meilin2026dh/pl5` 原仓库 Git blob SHA **逐字节相同**的原始TypeScript模块（见 `github_vendor/`）：

| 原版路径 | 用途 | Git blob SHA |
|---|---|---|
| `server/provider.ts` | 中国体育彩票官方开奖数据解析、获取、期号冲突校验 | `43f2c05896d728f97fdcc64a7b64988e3785b88c` |
| `src/lib/candidates.ts` | 五位号码大底解析及交并差/对称差 | `58e63cbda68c9317519cbb8f339f2d78653a2c78` |
| `src/domain/math.ts` | 质合、GCD、LCM、逆序数、乘积尾等原生数学指标 | `5d3725d839d29375d3ab785849998bba87891717` |
| `src/domain/backtest.ts` | 逐期历史回放及前缀截止规则 | `a71ecd6166d867e46e3f36d29cce758ba4e6a79b` |

**仓库审阅时版本**：`meilin2026dh/pl5` 的 `main` 提交 `9eb9ec5ad542877680755bccf27345298ef7b99f`（2026-11-01）。  
**原版完整GitHub源码仍需联网克隆到`D:\pl5\frontend`，或由用户已有的完整仓库提供。** 当前运行容器不能联网下载整个仓库；本ZIP不包含275个仓库文件，不对此作虚假声明。安装脚本在Windows上执行受控克隆，原有仓库不会被强制同步或覆盖。`github_vendor/`可离线阅读以上四个原始模块，但不是可单独启动的完整React项目。

## 研发改进：完整位图交叉检查

V1.2只能验证两个引擎的保留注数相等，存在“剩余数量一样、具体号码不同却漏报”的漏洞。V1.3新增：

1. 浏览器Worker发送严格AND**完整100000位掩码**，Python重新交集并逐位对比。
2. 基础规则的独立Python实现：`sum`、`tail`、`span`、`odd`、`big`、`prime`（彩票指标含1）、`distinct`、`repeat`、`consecutive`、`sumMod3`、`dan`、`kill`，逐条核对**100000个号码**。仅输入来源域内算通过/排除；支持include/exclude。
3. 每个规则返回是否进行了独立复算；其余GitHub复杂规则仍使用原生TypeScript位图，不得声称独立数学验证。
4. 支持从V1.2升级已存在的前端补丁，拒绝覆盖用户自行修改的接入文件，保存`.v12-before-v13.bak`。
5. 继续保留Python科研后端既有全部功能，新增V1.3接口测试。

## 安装到D盘

1. 先备份自己 `D:\pl5` 的重要文件。下载本ZIP并解压。
2. 双击 `install_to_D_v13.bat`。若`D:\pl5\frontend`不存在，需要联网访问GitHub，安装脚本克隆完整GitHub仓库并固定到审核时提交；如果已经存在完整前端，只在原有V1.2接入文件中安全升级，不执行`git pull/reset`。
3. 新Python后端放`D:\pl5\research_backend_v13`，四份原版源码归档到`D:\pl5\github_vendor_v13`；**旧版`research_backend_v12`、`data`、`runtime`及根目录程序均保留**。如果目标V1.3目录已存在，安装脚本拒绝覆盖。
4. 运行 `启动_V13_验证.ps1`，分别检验Python、GitHub前端测试、TS类型及生产构建。
5. 在两个PowerShell窗口分别运行 `启动_V13_科研后端.ps1` 和 `启动_V13_五序前端.ps1`；浏览器打开 `http://127.0.0.1:5173`。

技术要求：Python3.12+uv；Node24+pnpm11.25.0；完整前端需源代码和依赖安装。**程序尚未在你的Windows D盘执行安装**。

## 本容器内实际执行的验收

- `pytest -q`：后端 **191项全部通过**（原V1.2的172项 + 新增19项）。
- `node --experimental-strip-types github_vendor/tests/offline-smoke.mjs`：所复制的GitHub模块在Node22上完成7项离线断言。
- 集成测试：Node代理 → 127.0.0.1 Python服务，POST 10万位掩码，独立规则复算、完整交集相等、30注输出成功。
- 安装补丁测试：全新安装、V1.2原补丁升级、重复安装及用户修改阻断通过。
- `github_vendor`四模块Git blob SHA通过精确校验。

未完成：完整GitHub仓库的`pnpm test/typecheck/build`和浏览器人工验收（运行环境无法获取完整仓库及Node24）；官方数据API在此环境无法联网调用；彩票预测性能没有得到证实。

## 重要边界

每期100注命中的公平随机概率仍为0.1%，连续10期至少命中一次约0.9955%。多规则过滤与人工雕塑不会凭空提高该概率。ESSE评分属于研究性启发式评分，不是经校准的真实中奖概率。所有涉及外部数据与算法生成的科研操作仍应采取隔离、审计和人工准入。
