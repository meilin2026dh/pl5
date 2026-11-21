# PL5 V3.7.26 外部出题和第三方结算协议

这是可供真正独立评测者使用的 **技术接口**。代码、数据及本地实验本身不构成外部独立盲测。

### 独立出题方须做的事

- 在研究人员不能访问的计算机、账号、存储库中设计至少10种任务，至少包括新型结构、随机/负对照及训练标签异常；事前注册允许模型的输入、训练/验证/隐藏持出比例、预算与成功标准。
- 用JSON提交 `{task_id,source_description,train,validation,holdout}`，所有数据格式为 `[[a,b,y],...]`，三个分区坐标不重叠，取值为0至9的整数；模型看到的只有训练与验证以及秘密持出摘要。
- 在不同隔离环境中分别执行 `prepare`、`solve`、`grade`，并在冻结后才允许评测方读取私有答案。不能让求解方访问带有`holdout`或`nonce`的私有JSON。
- 对公开协议、求解程序哈希、冻结文件哈希取得独立签名/可信时间证明；保存出题方资格、权限审计及目标任务此前未公开的证明。
- 测算同一硬件的进程CPU时间、总墙钟时间及能源消耗；对所有挑战任务（含弃权）给出任务层正确率和适当置信区间，不能只报告接受任务的正确率。

### 交接命令

在`research_backend`目录：

```bash
python research_external_challenge_v3726.py prepare --challenge challenge.json --public PUBLIC --private PRIVATE
python research_external_challenge_v3726.py solve --public PUBLIC/public_challenge.json --out SOLVER
python research_external_challenge_v3726.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER
```

注意：当前`prepare`沿用V3.7.25的发行方摘要格式，V3.7.26模型本身使用其训练/验证协议摘要绑定，持出摘要由独立评测方在`grade`时核验；任何看见私有数据的同机演示必须明确写作 **内部演示**。文件摘要SHA256可发现意外修改，但不是数字签名，也不能证明独立身份或发布时间。

### 预先承诺的拒绝标准

- 如果公开JSON、冻结代码、隐藏答案承诺不一致，或出现可见的先验测试答案，立即判定评测无效。
- 如果任一算法超过预注册计算预算，应计为超预算，不能悄悄扩大预算后继续算作通过。
- 多次自适应观察持出结果并调整算法，会破坏“一次性盲测”性质；必须另取全新保密任务。

本次压缩包中测试的任务均由研发方设定、答案可在源码复现，**不能称第三方盲测**。
