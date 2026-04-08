# 银行风控项目计划（当前唯一执行计划）

> 若与 `README.md`、`MVP.md`、`nowthink.md`、`math.md` 或其它说明文档冲突，以本文件为准。

## 1. 当前阶段

- 当前阶段：`V4 / Phase-1（感知层能力建设）`
- `V3-beta` 状态：已收口并通过验收，可进入 `V4`。
- 当前热路径策略保持不变：
  - `precheck` 继续走知识库 + 规则引擎
  - Agent 继续只用于 `secondary-check`
  - `precheck all-Agent` 继续只做 shadow mode

## 2. 当前默认决策

- 不切 LangGraph/LangChain 主编排。
- 不新增决策枚举，不修改现有 REST 语义。
- MCP 只提供审计/能力暴露，不作为数据库本体。
- `V4 / Phase-1` 只做感知层，不扩展治理层规则口径。
- 结果同步文档最少包含：
  - `plan.md`
  - `MVP.md`
  - `README.md`

## 3. V4 准入检查表

| 检查项 | 结果 | 证据 |
|---|---|---|
| V3-beta 全链路验收 | 通过 | 后端 `55 passed`；Flutter `widget_test.dart` 全通过；`flutter analyze` 无问题 |
| 性能门限 | 通过 | `precheck warm p95=42.34ms`；`secondary warm avg=61.56ms`；LLM path `p95=5905.08ms` |
| MCP 审计查询稳定 | 通过 | `trace_events` 与 MCP 查询回归通过，拒绝分支 reason 可观测 |
| 感知层输入字段冻结 | 通过 | 以当前 `ClientContext` 字段为 V4-Phase1 冻结基线，新增字段仅允许向后兼容扩展 |

**准入结论：** `V4 / Phase-1` 已满足启动条件，按本计划执行。

## 4. V4 / Phase-1 实施内容（仅感知层）

### 阶段 A：感知输入契约冻结
1. 固化 `ClientContext` 感知字段基线（设备、位置、页面行为、语义摘要、微行为信号）。
2. 明确字段扩展规则：仅新增可选字段，不破坏现有请求体兼容性。
3. 统一字段命名与类型约束，避免前后端歧义。

### 阶段 B：MCP 感知能力补齐
1. 梳理感知层 MCP 工具输入输出契约。
2. 对外部感知能力增加超时、降级和失败分类。
3. 保证感知层异常不影响主裁决链路可用性。

### 阶段 C：可观测性与数据流一致性
1. 在审计 payload 中补齐感知字段摘要与关键耗时切片。
2. 确保感知层输出到识别层的变量流在 `math.md`/`nowthink.md` 中一致。
3. 保持 Trace 独立链路，不把审计写入耦合进核心裁决。

### 阶段 D：V4-Phase1 验收
1. 向后兼容回归：现有 `precheck / secondary-check / confirm / cancel` 不回归。
2. 感知字段契约回归：新增字段缺省时，旧请求路径行为不变。
3. 性能回归：`precheck warm p95 <= 750ms`，`secondary avg <= 3s` 持续达标。

## 5. 关键接口与数据边界

### 保持不变的 REST 接口
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/transfers/cancel`

### 本阶段允许变化
- 感知层内部契约与 MCP 工具能力增强
- 审计字段增强（不破坏现有查询语义）

### 本阶段禁止变化
- 决策枚举和对外响应语义
- 将 `precheck` 切换为 mandatory Agent
- 治理层规则口径扩张（留到 `V5`）

## 6. 性能目标与最新实测

- 目标：
  - `precheck warm-path p95 <= 750ms`
  - `deterministic risk decision subpath <= 300ms`
  - `secondary-check avg <= 3s`
  - `LLM path P95 <= 30s`
- 最新实测（2026-04-08）：
  - 后端回归：`55 passed`
  - baseline：
    - `precheck cold avg/p95 = 39.63ms`
    - `precheck warm avg = 31.43ms`
    - `precheck warm p95 = 42.34ms`
    - `secondary cold avg/p95 = 178.37ms`
    - `secondary warm avg = 61.56ms`
    - `secondary warm p95 = 111.77ms`
  - 真实 LLM benchmark：
    - `status = ok`
    - `avg_ms = 5403.69`
    - `p95_ms = 5905.08`
  - precheck all-Agent shadow：
    - `status = ok`
    - `avg_ms = 2282.41`
    - `p95_ms = 2530.10`
    - `decision_drift_rate = 0.0`
  - Flutter：
    - `flutter test test/widget_test.dart` 全通过（14/14）
    - `flutter analyze` 通过（No issues found）

## 7. 后续版本触发条件

### V5
- V4 感知层契约稳定
- 治理层拒绝口径稳定
- Trace 字段足够支持人工复核

目标：
- 完善治理层能力
- 落地初版风险报告 Agent

---

更新日期：2026-04-08  
当前执行阶段：`V4 / Phase-1`
