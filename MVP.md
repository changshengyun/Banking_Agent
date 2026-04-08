# HIRD 手机银行风控系统 · MVP 版本台账

> 本文档是版本台账、完整度评估和里程碑路线图。  
> 当前唯一活动执行计划见 `plan.md`。

## 1. 当前完整度评估

### 验证基线（最新实测）
- 后端核心回归：`55 passed`
- 前端自动化：`widget_test.dart` 全通过（14/14），`flutter analyze` 通过
- 本地性能基线：
  - `precheck cold_start avg/p95 = 39.63ms`
  - `precheck warm_path avg = 31.43ms / p95 = 42.34ms`
  - `secondary-check cold_start avg/p95 = 178.37ms`
  - `secondary-check warm_path avg = 61.56ms / p95 = 111.77ms`
- LLM 基准状态：
  - isolated LLM path benchmark：`status=ok`，`avg 5403.69ms / p95 5905.08ms`
  - precheck all-Agent shadow benchmark：`status=ok`，`avg 2282.41ms / p95 2530.10ms / drift 0.0`

### 功能完整度
| 维度 | 状态 | 说明 |
|---|---|---|
| 预检风控主链路 | 已完成 | `pass / interrogate / block` 稳定 |
| 二次质询单轮策略 | 已完成 | 同 token 单轮一次提交，未通过不可确认 |
| 显式取消交易 | 已完成 | `POST /api/v1/transfers/cancel` 已打通 |
| 三类 Agent 分工 | 已完成 | 初分 / 细分 / 语义分析职责固化 |
| 语义否定识别 | 已完成 | 已支持否定句冲突消解 |
| Trace 审计能力 | 已完成 | 事件链与最小时延字段已稳定 |
| MCP 审计查询 | 已完成 | `get_transfer_trace / list_transfer_traces` 可用 |
| 感知层全能力 | 进行中 | 作为 `V4 / Phase-1` 主线 |
| 治理层完善与风险报告 | 未开始 | 作为 `V5` 主线 |

### 当前结论
- `V3-beta` 已收口完成并通过验收，已满足进入 `V4` 条件。
- 当前执行主线已切换为：`V4 / Phase-1（感知层能力建设）`。

## 2. 当前架构快照

### HIRD-H 感知集成层
- 输入：`ClientContext`、交易金额、收款人、设备/城市/页面行为。
- 现状：已接入上下文、外部情报、基础行为信号。
- 下一步：V4 补齐 MCP 感知能力与字段契约冻结。

### HIRD-C/R 认知决策层
- `RiskKnowledgeBase`：场景检索、关键词/高危短语、`c_match`。
- `AgentService`：二次质询语义分析、红旗识别、`secondary_risk`。
- 三类 Agent 职责固定：领域初分、领域细分、语义分析。

### HIRD-G 治理控制层
- `RiskEngine`：执行 `w_adj / f_final` 主公式和阈值路由。
- 规则优先于 Agent 建议。
- 审计链路独立，Trace 可经 MCP 查询。

### HIRD-E 业务执行层
- 当前业务动作：`confirm / cancel / secondary-check`。
- 取消交易是显式业务动作，不与关闭弹窗混淆。

## 3. 版本总览

| 版本 | 核心目标 | 状态 | 说明 |
|---|---|---|---|
| V1 | 初版规则风控闭环 | 已归档 | 规则预检 + 基础拦截 |
| V2 | 场景扩展与 explain_pack | 已完成 | 风险场景扩容、解释面板稳定 |
| V3-alpha | 交互治理收口 + 三类 Agent + 单轮二次质询 | 已完成 | 主链路闭环完成 |
| V3-beta | 取消交易全链路统一 + 指标化 + Trace 审计入 MCP + 性能/真实 LLM/等待体验收口 | 已完成 | 验收通过 |
| V4 / Phase-1 | 完善 MCP 感知层能力与字段契约 | 进行中 | 仅感知层，不扩治理层 |
| V5 | 完善治理层 + 初版风险报告 Agent | 规划中 | 规则完善、报告生成、人工复核支持 |

## 4. V3-beta 收口结果

### 已完成项
1. 全链路稳定：`precheck -> secondary-check -> confirm/cancel`。
2. 单轮二次质询：一次提交、非 `pass_secondary` 不可确认。
3. 取消交易闭环：`pending -> cancelled` 语义稳定。
4. 性能/基准/真实 LLM/shadow benchmark 全部可跑并达标。
5. 前端等待态、防重复提交、长等待提示已通过自动化验证。

### 关闭判断
- 收口结论：`Closed`
- V4 准入：`Go`

## 5. V4 / Phase-1 路线

- 感知输入字段冻结与向后兼容扩展策略。
- MCP 感知能力补齐（超时、降级、失败分类）。
- 感知层数据流与可观测字段统一到 `nowthink.md` / `math.md`。

## 6. V5 路线

- 完善治理层规则编排和拒绝口径一致性。
- 增加初版风险报告 Agent：
  - 汇总风险因子
  - 输出结构化风险摘要
  - 给出建议动作

## 7. 文档导航

- `README.md`：项目总入口与启动/验证说明
- `plan.md`：当前唯一执行计划
- `nowthink.md`：Ideal、完整架构、数据流、代码映射、最终指标
- `math.md`：公式、变量流、场景算例、时延目标推导
- `promode/`：执行约束与协作规则

---

更新日期：2026-04-08  
当前主版本：`V4 / Phase-1（进行中）`  
上一版本状态：`V3-beta（已收口完成）`
