# PL5 V1.2｜五序统一平台 × 自进化解空间雕塑引擎

这是**增量融合部署包**，不是声称包含GitHub仓库全部源码的替代包。

- **Github原项目**：[`meilin2026dh/pl5`](https://github.com/meilin2026dh/pl5)，继续作为React工作台、原生过滤规则及官方历史服务。
- **本包 `github_overlay/`**：向现有GitHub前端新增“ESSE · V1.2融合雕塑”组件与Worker，Node同源代理，附测试。
- **本包 `research_backend/`**：保留此前Python V1.1研究模块，增加跨语言位图协议、可信输入校验与独立HTTP API。
- **本包 `integration_tests/`**：针对已有GitHub源码以严格锚点安装两处补丁，预先备份，重复安装幂等。
- **本包 Windows脚本**：安装到`D:\pl5\frontend`和`D:\pl5\research_backend_v12`，不直接覆盖旧版`D:\pl5`代码。

## 快速启动

1. 下载、解压后运行`install_to_D_v12.bat`（需要Windows的D盘、Git及Python；先确保网络可访问GitHub）。
2. 第一个PowerShell：`powershell -ExecutionPolicy Bypass -File .\启动_V12_科研后端.ps1`
3. 第二个PowerShell：`powershell -ExecutionPolicy Bypass -File .\启动_V12_五序前端.ps1`
4. 浏览器访问`http://127.0.0.1:5173`，在“缩水工作台”下找到“ESSE · V1.2融合雕塑”。

运行前请阅读[部署与接口说明](V12_部署与接口说明.md)。

## 兼容边界

V1.2仅桥接**严格AND规则**。容错组、按违规次数容错等语义会拒绝转译；不声称兼容尚未实现的全部高级功能。它把GitHub版每条规则的原生过滤结果作为基准，并交由Python ESSE计算可解释的雕塑路径，返回Top-K研究性候选。Python端的审核只证实位图完整性、规则交集和来源域保护，不等于对所有TypeScript算法进行了独立实现复现。

公平独立开奖时，任意100注的单期精确命中概率为0.1%，10期至少一次的基线约0.996%；新增的“偏好分”不得被描述为真实中奖概率。

## 本次测试（开发容器）

- Python版本持续回归：**172项pytest测试通过**（包含既有V1.1的模块测试和新增桥接测试）。
- Python HTTP→Node同源代理→Python雕塑：跨进程HTTP 200、原生交集一致及外部大底边界检查通过。
- Node代理脚本语法检查通过；新增TypeScript/TSX文件已完成转译语法检查。
- GitHub前端`pnpm test`、`pnpm typecheck`、浏览器真实交互 **尚未在完整GitHub源码中运行**（当前执行容器无法直接联网clone），需Windows部署后完成。Github原仓库中的测试数量以其仓库记录为准，不混算到上述172项。

**状态**：可部署的兼容桥接研发版，需GitHub原源码安装和Windows实机验收；GitHub主分支未被本交付修改。
