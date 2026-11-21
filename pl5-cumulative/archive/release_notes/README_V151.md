# PL5 V1.5.1 — 五序真实源码与科研后端联调版

本版是 **V1.5 的系统联通与可观测性补丁**，没有新增彩票预测能力。保留V1.5的自主科研、ESSE、注册审批、竞争扫描和冻结规则机制。

## 已新增（可执行源代码）

1. Python只读 `/api/esse/status`：汇总算法状态、最近一次扫描、暂停、账本链验证，以及官方接口本地缓存状态。使用 SQLite `mode=ro`，不会初始化缺失的数据库或改变算法审批状态。
2. 五序 React `EvolutionStatus` 面板：刷新、在线状态、候选/批准/暂停数量、竞争报告摘要，以及公平开奖适用限制。
3. Node同源 `/api/esse/status` 代理：沿用既有回环地址Python桥接，不暴露外部主机。
4. GitHub安全补丁：支持从无ESSE集成的五序源码或V1.2—V1.5集成版本升级；已存在用户定制文件或不匹配锚点则停止而不覆盖。原文件创建 `.before-v151.bak` 备份。
5. 跨进程 HTTP 集成测试、重复升级与用户修改拒绝测试。

**注意：** 本包内包含Python V1.5完整研发源码与增量前端模块，但不声称完整GitHub原仓库已被复制到ZIP。在Windows首次安装时，通过Git克隆 `https://github.com/meilin2026dh/pl5` 并固定到已评审提交 `9eb9ec5ad542877680755bccf27345298ef7b99f`。若 `D:\pl5\frontend` 已存在，则直接复用、不自动拉取或重置。克隆前应自行确认仓库的最新变更是否需另行合并。

## Windows安装

前提：Windows D盘、Git（如首次克隆）、Python、uv、Node.js 24、pnpm 11.25.0、网络（首次安装依赖）。

1. 下载并解压本ZIP，双击 `install_to_D_v151.bat`。
2. 新建 `D:\pl5\research_backend_v151` 和 `D:\pl5\github_vendor_v151`，不覆盖旧版研究后端、数据与runtime。
3. PowerShell运行 `./验证_V151.ps1`：后端pytest、前端pnpm test/typecheck/build；如果两个服务同时在线，还检查跨服务GET返回协议版本。
4. 分别打开两个PowerShell窗口运行 `./启动_V151_科研后端.ps1`、`./启动_V151_五序前端.ps1`。
5. 浏览器打开 `http://127.0.0.1:5173`（开发）或根据Node服务情况使用3001端口。进入「缩水工作台」，找到「算法竞争与进化中心 · 运行状态」；点击刷新。
6. 打开「历史走势」并主动从官方接口刷新历史；缓存文件为 `D:\pl5\frontend\.cache\history.json`。刷新后重新加载状态面板。

注意实际运行顺序：状态面板只读取已有扫描报告。运行V1.5 `research_v15.py scan` 后，才会出现非空的最近扫描；不会由UI自动发起扫描或审批。

## 数据与安全边界

- 缓存只有在来源URL字段符合预期、内容可解析、无过期标记且更新时间不超过36小时的情况下，才显示 `fresh_structurally_valid`。它不表示已经获得密码学真实性证明。
- 没有自动启动Windows任务计划；没有付费模型、投注操作、自动规则审批。
- 任何时期100注不同号码，公平独立开奖假设下单期精确命中概率仍为0.1%。
- 公网部署不在本版范围；本地回环桥接没有公共登录认证，不应将接口开放给公共互联网。

## 本环境已做的验收

- Python V1.5继承功能以及新状态模块的210项自动化测试。
- V1.5.1新增Node→Python真实TCP/HTTP冒烟测试；不是Mock。
- GitHub补丁：干净仓库锚点模拟、新版本再次运行不修改、自定义代理修改后拒绝覆盖、失配源码拒绝改写。
- **未在Windows实机完成**完整Github React构建和用户交互：当前环境无法连接GitHub仓库下载完整前端，且仅提供Node.js 22（原仓库要求Node.js 24）。

## 文件入口

- `research_backend/status_v151.py` — 只读状态聚合
- `research_backend/integration_server.py` — Python桥接服务
- `github_overlay/src/components/EvolutionStatus.tsx` — React状态卡
- `github_overlay/server/esseProxy.mjs` — Node代理
- `integration_tests/upgrade_github_overlay_v151.py` — 安全增量安装
- `integration_tests/test_live_v151.py` — 真实跨进程HTTP
- `install_to_D_v151.bat` — Windows安装
- `验证_V151.ps1` — 完整依赖、测试、构建及在线检查

V1.5的现有定时科研仍使用独立的用户授权启动机制，本版没有自动开启。新状态页也不是科研任务管理控制台。
