# 银行风控项目计划（当前唯一执行计划）

> 若与 `README.md`、`MVP.md`、`nowthink.md`、`math.md` 或其它说明文档冲突，以本文件为准。

## 1. 当前阶段

- 当前阶段：`V5 / Phase-1（启动准备中）`
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

## 2. V4 收口结果

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

## 3. 当前接口边界

### 3.1 保持不变
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/transfers/cancel`
- 现有决策枚举与响应语义

### 3.2 已交付新增接口
- `GET /api/v1/transfers/{confirmation_token}/risk-report`
- 风险报告 schema / 展示模型

### 3.3 继续禁止
- 新增业务裁决枚举
- 让风险报告 Agent 直接参与裁决
- 将 `precheck` 切换为 mandatory Agent 热路径

## 4. V5 / Phase-1 当前目标

1. 深化治理层拒绝口径与策略编排一致性。
2. 增强风险报告质量、模板治理和可复核性。
3. 评估是否需要报告历史中心、人工复核辅助入口和更细粒度报告追踪字段。
4. 保持每轮开发后同步 `plan.md / MVP.md / README.md`，涉及架构或变量流时同步 `nowthink.md / math.md`。

## 5. 当前下一步

1. 以 `V5 / Phase-1` 为新的唯一活动阶段，整理治理层与报告增强的具体任务拆分。
2. 在不改变现有业务裁决语义的前提下，定义报告增强范围和治理深化边界。
3. 保持 `V4` 已交付接口稳定，不为 V5 先行引入破坏性变更。
4. 大版本完成后继续执行：文档同步 -> `git add -> git commit -> git push`（默认当前工作分支）。

---

更新日期：2026-04-09  
当前执行阶段：`V5 / Phase-1（启动准备中）`
