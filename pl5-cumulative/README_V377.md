# PL5 V3.7.7 — 可学习的潜在数字原语（研究预览版）

版本基线：`PL5_V3.7.6_hotfix1_integrated.zip`。此包是 V3.7.7 **研究预览增量**；为保留历史版本一致性测试，后端 `pyproject.toml` 的正式应用版本号仍保持 3.7.6，待全平台验收后再升级。原累计源码和安全补丁不受影响。

## 新增（不替代旧功能）

- `research_backend/pailie5/latent_primitives_v377.py`：训练专用的有限群加法分解。通过二分图中的同余约束，从训练样本推导 `u(a),v(b)` 两个10元素映射，输出 `(u(a)+v(b))%10`。如果训练约束互相矛盾则拒绝；不能唯一识别全部输入时弃权。
- `research_backend/pailie5/primitive_study_v377.py`：锁定合成实验方案，分别对可分解结构、非可分解结构和随机真值表实施对照，不传入保留标签进行训练。
- `research_backend/research_primitive_v377.py`：命令行复现实验。结果使用排他写入，不会覆盖已有输出。
- `research_backend/tests/test_latent_*v377.py`、`tests/test_primitive_study_v377.py`：输入边界、训练/保留隔离、可重复性、负对照、方法拒绝等测试。
- `docs/v377/`：锁定协议、30组原始逐次结果、200组随机审计、开发试跑（与正式试验分离）、日志和报告。

## 运行

准备 Python>=3.12 和包依赖。Windows 示例：

```powershell
cd D:\pl5\research_backend
py -3.12 -m pip install -e .
py -3.12 -m pytest -q tests/test_latent_primitives_v377.py tests/test_latent_adversarial_v377.py tests/test_primitive_study_v377.py
py -3.12 research_primitive_v377.py --protocol ..\docs\v377\protocol.json --output ..\runs\v377_replay.json
```

注意：这段命令**没有在你的Windows主机执行**。请先备份已有 `D:\pl5`，勿直接覆盖原项目。重复运行时请选择不同输出文件名，避免无意覆盖研究证据。

## 研究意义与界限

- 这是从训练数据重建**指定模型类别**的两组数字映射，不是凭空发明普适数学定律，也没有打开任意生成代码的能力。
- 仅当输入表的结构可表示为上述形式，且训练约束识别充分，系统才输出一个算子。
- 15个不同参数的合成正对照均通过，15个合成负对照均拒绝；参照的旧AST搜索最大500次表达式评价，计算预算**未匹配**。
- 合成输入对分割的成功，不代表彩票时间序列的未来预测或过滤能力。所有候选的生产过滤始终关闭。
- V3.7.6 的旧自主科研控制器并未自动调用新算子；本版先交付一个可审计的独立研究模块，之后再考虑在批准的方法注册表中接入。
- 截至本轮，全量旧后端测试未能完整结束；相关范围测试和跨模块集成通过，不能称稳定版。
