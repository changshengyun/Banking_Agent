# work_now · 工作快照

> 本文档记录当前轮次的短周期任务快照、完成进度以及系统的当前性能指标。
> 任务完成后，请同步更新对应项。

---

## 1. 当前阶段

**阶段名称**：MVP V3-alpha 收口完成 / V3-beta 启动准备
**当前目标**：推进取消交易全链路统一与指标化，打通 Trace 审计写入 MCP，并冻结 V4/V5 需求口径。

---

## 2. 子任务列表

| # | 子任务 | Owner Agent | Acceptance Agent | 状态 | 开始时间 | 完成时间 | 备注 | Gate Result | Evidence | Blocker |
|---|---|---|---|---|---|---|---|---|---|
| **A1** | 文档治理原则 | Coordinator Agent | Acceptance Lead Agent | ✅ | 2026-04-07 | 2026-04-07 | plan.md 设为唯一执行计划 | PASS | — | — |
| **A2** | MVP/nowthink/work_now 重构 | Coordinator Agent | Acceptance Lead Agent | ✅ | 2026-04-08 | 2026-04-08 | 重写目标蓝图与架构意图 | PASS | — | — |
| **B1** | 无效输入提示统一 | Frontend UX Agent | Acceptance Sub-Agent C | ✅ | 2026-04-08 | 2026-04-08 | 文案统一为 `无效输入，请按照要求输入` | PASS | `flutter analyze --no-version-check lib/main.dart lib/banking_api.dart test/widget_test.dart`（No issues found） | — |
| **B2** | 取消交易入口显式化 | Frontend UX Agent | Acceptance Sub-Agent C | ✅ | 2026-04-08 | 2026-04-08 | “关闭/取消交易”边界分离，保持显式业务动作 | PASS | `flutter test --no-version-check test/widget_test.dart`（All tests passed） | — |
| **B3** | 数学公式落地 | Risk Formula Agent | Acceptance Sub-Agent B | ✅ | 2026-04-08 | 2026-04-08 | `w_base=0.3` + `w_adj/f_final`；硬拦截优先 | PASS | `pytest server/tests/test_formula.py` | — |
| **B4** | 三类 Agent Prompt 契约对齐 | Prompt Contract Agent | Acceptance Sub-Agent A | ✅ | 2026-04-08 | 2026-04-08 | `domain/deep/semantic` 输出映射到 `SecondaryResult.*_output` | PASS | `pytest server/tests/test_patch2_secondary_followup.py` | — |
| **B5** | 二次质询稳定性优化（不改语义） | Backend Flow Agent | Acceptance Sub-Agent A | ✅ | 2026-04-08 | 2026-04-08 | 增加状态校验与拒绝口径统一（重复提交/非pending） | PASS | `pytest server/tests/test_api.py -k "secondary_check_rejects_cancelled_transfer or secondary_check_rejects_committed_transfer"` | — |
| **B6** | V3 联调自动化脚本补齐 | Backend Flow Agent | Acceptance Sub-Agent D | ✅ | 2026-04-08 | 2026-04-08 | 新增 `interrogate->cancel/pass_secondary/block_secondary` 三条集成路径自动化用例 | PASS | `pytest server/tests/test_v3_integration_flows.py`（3 passed） | — |
| **B7** | API 契约快照与性能基线写实 | Coordinator Agent | Acceptance Lead Agent | ✅ | 2026-04-08 | 2026-04-08 | 新增 `docs/api-contract-v3.md` 和性能采样脚本 | PASS | `python server/tests/benchmark_v3_baseline.py`（产出 avg/p95） | — |
| **D1** | Gate A/B/D 后端总验收 | Acceptance Lead Agent | Acceptance Sub-Agent D | ✅ | 2026-04-08 | 2026-04-08 | 单轮质询、取消链路、公式与场景回归通过 | PASS | `pytest server/tests/test_formula.py server/tests/test_api.py server/tests/test_patch2_secondary_followup.py server/tests/test_risk_scenarios.py server/tests/test_v3_integration_flows.py`（46 passed） | — |
| **D2** | Gate C 前端验收 | Acceptance Lead Agent | Acceptance Sub-Agent C | ✅ | 2026-04-08 | 2026-04-08 | 修复二次质询弹窗输入生命周期，Gate C 全量通过 | PASS | `flutter analyze --no-version-check lib/main.dart lib/banking_api.dart test/widget_test.dart` + `flutter test --no-version-check test/widget_test.dart` | — |
| **E1** | V3-beta 取消交易全链路统一与指标化设计 | Backend Flow Agent | Acceptance Sub-Agent A | ⏳ | 2026-04-08 | — | 定义取消链路步骤、状态机边界与指标字段 | PENDING | 待补（设计文档 + 回归命令） | — |
| **E2** | V3-beta Trace 审计写入 MCP | Backend Flow Agent | Acceptance Sub-Agent D | ⏳ | 2026-04-08 | — | Trace 字段模型、写入链路、查询接口最小闭环 | PENDING | 待补（接口用例 + 数据样例） | — |
| **E3** | V4 感知层 MCP 能力清单冻结 | Coordinator Agent | Acceptance Lead Agent | ⏳ | 2026-04-08 | — | 完善多模态信号与外部情报 MCP 接入需求 | PENDING | 待补（能力矩阵） | — |
| **E4** | V5 治理层与风险报告 Agent 设计 | Prompt Contract Agent | Acceptance Sub-Agent B | ⏳ | 2026-04-08 | — | 初版报告 Agent 输出结构与治理层增强范围 | PENDING | 待补（Schema + 示例报告） | — |

---

## 3. 当前功能性能

| 功能模块 | 指标项 | 当前值 | 目标值 | 评估日期 | 备注 |
|---|---|---|---|---|---|
| **核心接口** | `/precheck` 平均时延 | 29.66ms | < 500ms | 2026-04-08 | 本地 TestClient 50 轮基线 |
| | `/secondary-check` 平均时延 | 43.99ms | < 3s | 2026-04-08 | 本地 TestClient 30 轮基线（单轮通过路径） |
| **风险决策** | 场景分类准确率 | — | > 90% | — | 基于向量知识库 |
| | 语义红旗命中率 | — | > 85% | — | 对已知被教唆样本 |
| **系统底座** | 知识库 Top-1 命中率 | — | > 95% | — | TF-IDF / Embedding |
| | LLM P95 推理延迟 | 未单独采样 | < 5s | 2026-04-08 | 当前基线包含本地快速判定路径 |

> **注**：性能指标字段目前为占位状态，随子任务 B/C/D 的推进逐步补填实际测试数据。

---

## 4. 更新记录

| 日期 | 操作人 | 更新内容 |
|---|---|---|
| 2026-04-08 | Codex | 根据最新版本规划更新路线：V3-beta=取消交易全链路统一与指标化+Trace写入MCP，V4=完善MCP感知层，V5=完善治理层+初版风险报告Agent；新增 E1-E4 待执行任务。 |
| 2026-04-08 | Codex | 完成 V3 P0 收口：新增 `test_v3_integration_flows.py`（3 条联调路径）、新增 `docs/api-contract-v3.md` 契约快照、新增 `benchmark_v3_baseline.py` 并回填性能基线；后端总回归更新为 46 passed。 |
| 2026-04-08 | Codex | 同步文档基线：新增 `development_todo.md`（架构总览/版本进度/V3->V5 TODO），更新 `MVP.md` 为版本台账；后端总回归结果同步为 43 passed。 |
| 2026-04-08 | Codex | 前端修复完成：移除二次质询弹窗临时 `TextEditingController`，改为 `onChanged` 采集，消除 `used after disposed`；同步稳定化取消交易用例断言；Gate C 从 BLOCKED 更新为 PASS。 |
| 2026-04-08 | Codex | 新增二次质询边界回归用例（cancel/confirm 后 secondary-check 拒绝），后端总回归更新为 40 passed；遵循“仅改项目代码，不触碰 Flutter SDK”执行。 |
| 2026-04-08 | Codex | 实施分层并行方案：落地风险公式、三类Agent契约、二次质询稳定性优化；完成 Gate A/B/D 后端验收并记录 Gate C 阻塞证据。 |
| 2026-04-08 | Claude | 完成文档重组：重写 MVP.md, nowthink.md, work_now.md 结构，按新口径同步。 |
| 2026-04-07 | Claude | 启动文档治理阶段，固化 plan.md 唯一来源地位。 |
| 2026-04-07 | Claude | 确认当前版本为 V3-alpha 交互与治理收口前置阶段。 |

---

**下一步工作建议**：
1. 进入 V3-beta：统一取消交易全链路步骤并补齐指标化字段。
2. 进入 V3-beta：完成 Trace 审计写入 MCP 与最小查询闭环。
3. 启动 V4 需求冻结：完善 MCP 感知层能力矩阵与接入契约。
4. 启动 V5 需求冻结：完善治理层范围并定义初版风险报告 Agent 输出结构。
