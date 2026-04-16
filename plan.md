# 银行风控项目计划（当前唯一执行计划）

> 若与 `README.md`、`MVP.md`、`nowthink.md`、`math.md` 或其它说明文档冲突，以本文件为准。

## 1. 当前阶段

- 当前阶段：`V5 / Phase-3（复核筛选、时间线语义修正与稳定性收口进行中）`
- 上一活动版本：`V4（已完成并收口）`
- 当前版本边界结论：
  - `V4` 已完成“感知层 + 初版风险报告 Agent”双主线交付。
  - 原 `V5` 的初版风险报告工作已在 `V4` 内完成。
  - 新的 `V5` 定义为：治理深化 + 报告增强。
  - 原 `V3` 性能优化线继续冻结，仅保留观测，不作为当前阻塞项。
- `V4` 收口结论（2026-04-09）：
  - 后端风险报告链路已落地，`GET /api/v1/transfers/{confirmation_token}/risk-report` 可用。
  - `secondary-check` 后已生成并持久化结构化风险报告，同时写入 `trace_events.risk_report_generated`。
  - Flutter 已补齐最小可用的风险报告查看入口。
  - 后端回归已通过：`58 passed`。
  - 前端正式验收已通过：
    - `flutter analyze --no-version-check` -> `No issues found!`
    - `flutter test --no-version-check test/widget_test.dart` -> `All tests passed!`
  - 之前的“Flutter 超时阻塞”已确认为环境问题，根因是：
    - Flutter SDK Git 信任异常
    - `flutter analyze` 曾在错误目录执行

## 2. V5 / Phase-1 已完成基础（2026-04-09）

1. 增强风险报告治理元数据：
   - 新增报告版本、策略版本、生成模式、来源阶段、二次结论、风险分类、外部情报等级、关联审计事件。
2. 将风险报告从“可读摘要”提升为“可复核产物”：
   - 报告持久化已新增治理上下文字段。
   - 报告生成 trace 已补充 `report_version / generation_mode / policy_version`。
3. Flutter 风险报告面板已新增“治理上下文”展示区。
4. Phase-1 验证已通过：
   - 后端：`58 passed`
   - Flutter analyze：`No issues found!`
   - Flutter widget test：`All tests passed!`

## 3. V5 / Phase-1 已完成增项（2026-04-09）

1. 新增“我的页风险报告中心”：
   - 首版入口固定在 Flutter“我的”页。
   - 默认仅展示当前用户最近 20 条高风险报告。
2. 新增风险报告列表接口：
   - `GET /api/v1/transfers/risk-reports`
   - 语义固定为当前用户高风险报告列表，不做筛选参数扩展。
3. 前端已支持：
   - 风险报告中心列表展示
   - 空态
   - 错误态 + 重试按钮
   - 点击列表项复用现有报告详情面板
4. 后端列表查询直接基于 `risk_reports` 持久化数据，不通过 trace 反查，不做现算。

## 4. V5 / Phase-2 本轮完成项（2026-04-09）

1. 新增人工复核单域模型：
   - `manual_review_cases` 已持久化 `review_id / confirmation_token / status / outcome / request_reason / request_snapshot / review_note / reviewer_id / submitted_at / updated_at / closed_at`。
   - 同一 `confirmation_token` 当前最多允许 1 个未关闭复核单。
2. 新增人工复核完整状态机与审计：
   - 固定状态流：`submitted -> in_review -> closed`
   - 固定关闭结果：`upheld / advisory`
   - trace 已新增：
     - `manual_review_requested`
     - `manual_review_started`
     - `manual_review_closed`
3. 新增后端人工复核接口：
   - `POST /api/v1/transfers/{confirmation_token}/manual-review`
   - `GET /api/v1/manual-reviews`
   - `GET /api/v1/manual-reviews/{review_id}`
   - `GET /api/v1/manual-reviews/queue`
   - `PATCH /api/v1/manual-reviews/{review_id}`
4. Flutter 已补齐“我的页人工复核闭环”：
   - “我的”页新增 `我的复核单`
   - 风险报告详情新增 `申请人工复核`
   - 同 App 内新增 `复核处理台`
   - 用户侧与处理台侧共用同一复核详情模型
5. 当前自动化验证已通过：
   - 后端：`63 passed`
   - Flutter analyze：`No issues found!`
   - Flutter widget test：`All tests passed!`

## 5. V5 / Phase-3 本轮完成项（2026-04-09）

1. 人工复核列表已新增状态筛选能力：
   - `GET /api/v1/manual-reviews?status=all|submitted|in_review|closed`
   - 首版固定按 `submitted_at` 倒序，仍保持最近 20 条边界。
2. Flutter“我的复核单”已新增筛选 chips：
   - `全部`
   - `待处理`
   - `处理中`
   - `已关闭`
3. Flutter“复核处理台”已新增队列筛选：
   - `全部`
   - `待处理`
   - `处理中`
4. 复核详情页已新增时间线视图：
   - `已提交`
   - `处理中`
   - `已关闭`
   - 时间线直接复用 `submitted_at / updated_at / closed_at / reviewer_id / outcome`
5. 当前自动化验证已通过：
   - 后端：`64 passed`
   - Flutter analyze：`No issues found!`
   - Flutter widget test：`All tests passed!`

## 5.1 V5 / Phase-3 稳定性修复（2026-04-10）

1. 人工复核错误语义已收敛：
   - 新增 `NotFoundError`
   - 人工复核与风险报告相关的资源不存在统一返回 `404`
   - 非法状态流转、重复申请、无效参数继续返回 `400`
2. 复核时间线语义已修正：
   - `manual_review_cases` 新增 `in_review_at`
   - 时间线改为展示 `submitted_at / in_review_at / closed_at`
   - 不再复用 `updated_at` 推断“处理中”时间
3. Flutter 人工复核状态展示已简化：
   - 状态颜色、状态文案、筛选文案、空态文案已收敛到统一 helper
4. 本轮自动化验证已通过：
   - 后端：`66 passed`
   - Flutter analyze：`No issues found!`
   - Flutter widget test：`All tests passed!`

## 6. V4 收口结果

### 2.1 已完成范围

#### Track-A 感知层
1. 冻结 `ClientContext` 契约，V4 范围内只做向后兼容扩展。
2. 以 `perception_snapshot` 统一沉淀设备、位置、页面行为、输入行为、语义摘要与外部情报摘要。
3. 在 `precheck`、`secondary-check`、报告生成链路中复用感知结果，不再多处重复拼装。
4. 在关键 trace payload 中补齐感知摘要和耗时字段。

#### Track-B 风险报告 Agent
1. 在 `secondary-check` 之后生成简版结构化风险报告。
2. 报告输入已覆盖：用户画像摘要、`semantic_summary`、二次回复、`risk_classification`、`secondary_decision`、`semantic_red_flags`、外部情报摘要、explain pack。
3. 报告输出已固定为：
   - `headline`
   - `overall_risk_level`
   - `risk_summary`
   - `risk_factors`
   - `recommended_action`
   - `evidence`
   - `generated_at`
4. 已采用“结构化持久化”方案，按 `confirmation_token` 查询。
5. 风险报告只做说明和建议，不参与业务裁决。

### 2.2 V4 验收结果
| 项目 | 结果 | 备注 |
|---|---|---|
| 后端回归 | 通过 | `58 passed` |
| Flutter analyze | 通过 | `No issues found!` |
| Flutter widget test | 通过 | `All tests passed!` |
| 文档一致性 | 通过 | `plan / MVP / README / nowthink / math` 口径已回正 |

### 2.3 V4 完成判定
- 当前按你的锁定标准执行：自动化通过即可视为 `V4` 达到完成门槛，不额外要求人工联调记录。
- 因此 `V4` 当前状态为：`已完成 / 已收口`。

## 7. 当前接口边界

### 3.1 保持不变
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/transfers/cancel`
- 现有决策枚举与响应语义

### 3.2 已交付新增接口
- `GET /api/v1/transfers/{confirmation_token}/risk-report`
- `GET /api/v1/transfers/risk-reports`
- `POST /api/v1/transfers/{confirmation_token}/manual-review`
- `GET /api/v1/manual-reviews`
- `GET /api/v1/manual-reviews?status=...`
- `GET /api/v1/manual-reviews/{review_id}`
- `GET /api/v1/manual-reviews/queue`
- `PATCH /api/v1/manual-reviews/{review_id}`
- 风险报告 schema / 展示模型
- 风险报告治理元数据（加法字段，保持向后兼容）
- 人工复核单 schema / 展示模型

### 3.3 继续禁止
- 新增业务裁决枚举
- 让风险报告 Agent 直接参与裁决
- 将 `precheck` 切换为 mandatory Agent 热路径

## 8. V5 / Phase-3 当前目标

1. 在不改变业务裁决语义的前提下，继续深化治理层拒绝口径与策略编排一致性。
2. 继续增强风险报告质量、模板治理、复核证据组织与时间线可读性。
3. 在现有“报告中心 + 人工复核闭环 + 状态筛选”基础上扩展更细粒度的报告追踪字段与治理说明。
4. 保持每轮开发后同步 `plan.md / MVP.md / README.md`，涉及架构或变量流时同步 `nowthink.md / math.md`。

## 9. 当前下一步

1. 继续深化人工复核与报告治理字段的联动展示，但不改 `precheck / secondary-check / confirm / cancel` 语义。
2. 评估 `V5 / Phase-4` 是否引入复核搜索、批量治理视图或更细粒度治理指标。
3. 保持 `V4` 与 `V5 / Phase-3` 已交付接口稳定，仅做向后兼容增强。
4. 每轮完成后继续同步文档并执行回归验证。

---

更新日期：2026-04-09  
当前执行阶段：`V5 / Phase-3（复核筛选与时间线追踪进行中）`
