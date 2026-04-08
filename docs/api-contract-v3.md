# API Contract Snapshot · V3-alpha

> 快照日期：2026-04-08  
> 目标：冻结当前 V3 对外接口语义，作为 V4 编排迁移前的契约基线。  
> 说明：本文件描述“接口语义约束”，执行计划仍以 `plan.md` 为准。

## 1. Transfer APIs

### `POST /api/v1/transfers/precheck`

Request
- `payee_name: str (1..40)`
- `amount: float (>0)`
- `context: ClientContext`

Response
- `decision: "pass" | "interrogate" | "block"`
- `risk_level: str`
- `flag_s, g_behavior, g_dynamic, final_risk: float`
- `reasons: list[str]`
- `confirmation_token: str`
- `assistant_message: str`
- `risk_classification: RiskClassificationPayload`
- `external_intelligence: ExternalIntelligenceReport`
- `explain_pack: ExplainPack`

Semantic constraints
- `decision=block` 时，后续 `confirm` 必须拒绝。
- `decision=interrogate` 时，需进入 `secondary-check`（单轮策略）。

### `POST /api/v1/transfers/secondary-check`

Request
- `confirmation_token: str`
- `user_reply: str (1..500)`
- `context: ClientContext`

Response
- `secondary_decision: str`
- `reasons: list[str]`
- `final_risk_after_secondary: float`
- `assistant_message: str`
- `semantic_red_flags: list[str]`
- `risk_classification: RiskClassificationPayload`
- `external_intelligence: ExternalIntelligenceReport`
- `explain_pack: ExplainPack`

Semantic constraints (V3 single-round)
- 同一 `confirmation_token` 仅允许成功提交一次 `secondary-check`。
- 非 `pending` 状态调用 `secondary-check` 必须返回 400。
- 首次结果：
  - `pass_secondary`：允许继续 `confirm`
  - `block_secondary`：禁止 `confirm`
  - `interrogate`：本轮未通过，禁止 `confirm`，且不得再次提交同 token 的 `secondary-check`

### `POST /api/v1/transfers/confirm`

Request
- `confirmation_token: str`

Response
- `success: bool`
- `assistant_message: str`
- `cash_balance, wealth_balance, total_assets: float`
- `latest_transaction: TransactionItem`

Semantic constraints
- 若 precheck 为 `interrogate`，且 `secondary_decision != pass_secondary`，必须返回 400。
- 已 `cancelled` 或已 `committed` token 必须拒绝再次确认。

### `POST /api/v1/transfers/cancel`

Request
- `confirmation_token: str`

Response
- `success: bool`
- `status: str`（当前为 `cancelled`）
- `confirmation_token: str`
- `assistant_message: str`

Semantic constraints
- 取消是显式业务动作，不能等价于关闭弹窗。
- 取消后 `confirm` 和 `secondary-check` 均应拒绝。

## 2. Classification & Chat APIs

### `POST /api/v1/transfers/classify-risk`
- 输入与 `precheck` 一致，输出为 `RiskClassificationPayload`。

### `POST /api/v1/agent/chat`
- 输入：`messages + context`
- 输出：`assistant_message + used_tools + suggested_actions`

## 3. Contract Stability Notes

- V3 迁移到 V4 前，不变更以下语义：
  - `DecisionType`：`pass/interrogate/block`
  - `secondary-check` 单轮一次提交规则
  - `cancel` 作为显式业务动作
  - `explain_pack` 节点结构（`static/behavior/semantic/external_intelligence/decision`）
