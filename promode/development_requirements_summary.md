# Development Requirements Summary

> 本文件汇总你在历史对话里明确过的开发要求，作为执行前必读清单。  
> 规则正文以 `promode/codex_execution_rules.md` 为准；活动执行以 `plan.md` 为准。

## 1. 执行总则

- 计划模式优先：先形成计划，再按 `plan.md` 执行。
- `plan.md` 是唯一活动执行计划来源。
- 能从仓库自证的问题直接执行，避免反复提问。

## 2. 多 Agent 协作要求

- substantial 任务默认按多 Agent 思路拆分。
- 必须有一个验收 Agent 负责总验收。
- 验收任务重时，允许拆多个子验收 Agent 并行。
- 多 Agent 写入范围不能重叠，避免并发改同一文件。

## 3. 实现边界

- 不改 Flutter SDK，只改项目代码。
- 保持对外 API 语义稳定，除非你明确要求改动。
- 先稳主链路，再做框架迁移或大规模重构。
- `precheck` 保持知识库 + 规则引擎热路径。
- Agent 主要用于 `secondary-check`；`precheck all-Agent` 只允许 shadow mode。
- Trace 是独立审计链路，不介入主裁决。

## 4. 文档同步要求

- 每次实现后至少同步：
  - `plan.md`
  - `MVP.md`
  - `README.md`
- 若涉及架构/公式/数据流变更，同步：
  - `nowthink.md`
  - `math.md`
- 避免多文档对同一阶段出现冲突口径。

## 5. Git 与交付要求

- Git 操作使用非交互命令。
- 不回滚你未明确要求回滚的改动。
- 仅在你明确要求提交/推送时执行对应操作。

## 6. 当前版本节奏（约束）

- `V3-beta` 重点：稳定性、性能、真实 LLM、等待体验收口。
- `V4` 重点：感知层能力完善（先不扩治理层）。
- `V5` 重点：治理层完善 + 初版风险报告 Agent。
