# HIRD 手机银行风控系统 · MVP 版本台账

> 本文档只负责版本台账、完整度评估和里程碑状态。  
> 当前唯一活动执行计划以 `plan.md` 为准。

## 1. 当前完整度评估

### 最新验证状态（2026-04-10）
- 后端核心回归：`66 passed`
- 前端正式验收：
  - `flutter analyze --no-version-check`：`No issues found!`
  - `flutter test --no-version-check test/widget_test.dart`：`All tests passed!`
- 之前的 Flutter 阻塞已解决：
  - 根因 1：Flutter SDK Git 信任异常
  - 根因 2：`flutter analyze` 曾在错误目录执行，导致分析范围跑偏到用户主目录
- 性能状态：
  - 继续保留基线观测
  - 当前不作为 `V4` 完成阻塞项

### 功能完整度
| 维度 | 状态 | 说明 |
|---|---|---|
| 预检风控主链路 | 已完成 | `pass / interrogate / block` 稳定 |
| 二次质询单轮策略 | 已完成 | 同 token 单轮一次提交，未通过不可确认 |
| 显式取消交易 | 已完成 | `POST /api/v1/transfers/cancel` 已打通 |
| 三类 Agent 分工 | 已完成 | 初分 / 细分 / 语义分析职责固定 |
| Trace 审计能力 | 已完成 | `risk_report_generated` 事件已稳定 |
| MCP 审计查询 | 已完成 | `get_transfer_trace / list_transfer_traces` 可用 |
| 感知层 V4 范围 | 已完成 | `perception_snapshot` 已进入 trace 与报告链路 |
| 风险报告 Agent 后端链路 | 已完成 | schema、service、repository、API、trace 已落地 |
| 风险报告 Agent 前端体验 | 已完成 | 查看入口与报告面板已通过自动化验收 |
| 性能专项优化 | 冻结 | 不再作为当前版本阻塞项 |

### 当前结论
- `V3-beta` 已完成并收口。
- `V4` 已完成并收口。
- 当前活动阶段已切换到：`V5 / Phase-3（进行中）`。
- 当前 `V5 / Phase-3` 正在做人工复核稳定性修复：
  - 资源不存在统一收敛为 `404`
  - 时间线改为真实展示 `submitted / in_review / closed` 三个时间点
- 原 `V5` 的“初版风险报告 Agent”已并入 `V4`。
- 新的 `V5` 定义为：治理深化与报告增强版本。

## 2. 版本治理规则

### 文档职责
- `plan.md`：唯一活动执行计划与当前阶段
- `MVP.md`：版本台账与里程碑状态
- `README.md`：对外入口与当前验证摘要
- `nowthink.md / math.md`：架构、变量流、公式与性能说明

### 每次开发后的同步要求
1. 同步 `plan.md`：阶段状态、本轮完成项、下一步。
2. 同步 `MVP.md`：版本状态与里程碑变化。
3. 同步 `README.md`：当前阶段与验证结论。
4. 若涉及架构或变量流，额外同步 `nowthink.md / math.md`。

### 大版本完成门槛
1. 满足 `plan.md` 中定义的版本验收项。
2. 通过：
   - `server\.venv\Scripts\python -m pytest server\tests -q`
   - `flutter analyze --no-version-check`
   - `flutter test --no-version-check test/widget_test.dart`
3. 文档同步且无口径冲突。
4. 满足后执行 `git commit + push`（默认当前工作分支）。

## 3. 当前架构快照

### HIRD-H 感知集成层
- 输入：`ClientContext`、交易金额、收款人、设备/城市/页面行为、输入微行为、外部情报
- 当前进展：
  - 已将关键感知信号沉淀为 `perception_snapshot`
  - 已在 `precheck`、`secondary-check` 和报告链路中复用

### HIRD-C/R 认知决策层
- `RiskKnowledgeBase`：场景识别、关键词/高危短语、`c_match`
- `AgentService`：二次质询语义分析、红旗识别、`secondary_risk`
- 风险报告 Agent 不参与业务裁决，只负责生成说明性报告

### HIRD-G 治理控制层
- `RiskEngine`：执行 `w_adj / f_final` 主公式和阈值路由
- `BankHostService`：主状态机、trace 审计、报告生成触发
- `RiskReportService`：在 `secondary-check` 后生成结构化报告并持久化
- `V5` 当前增量：报告已补充治理元数据和关联审计上下文

### HIRD-E 业务执行层
- 当前动作：`confirm / cancel / secondary-check / risk-report view`
- Flutter 已提供二次校验后查看报告的最小入口

## 4. 版本总览

| 版本 | 核心目标 | 状态 | 说明 |
|---|---|---|---|
| V1 | 初版规则风控闭环 | 已归档 | 规则预检 + 基础拦截 |
| V2 | 场景扩展与 explain_pack | 已完成 | 风险场景扩容、解释面板稳定 |
| V3-alpha | 交互治理收口 + 三类 Agent + 单轮二次质询 | 已完成 | 主链路闭环完成 |
| V3-beta | 取消交易统一 + 指标化 + Trace 审计入 MCP + 性能与体验收口 | 已完成 | 已验收 |
| V4 | 感知层 + 初版风险报告 Agent 双主线 | 已完成 | 前后端验收通过，已收口 |
| V5 | 治理深化 + 报告增强 | 进行中 | 已完成报告中心、人工复核闭环与复核筛选/时间线首版 |

## 5. V4 收口结果

### 已完成
1. 风险报告持久化与查询接口已落地。
2. `secondary-check` 后自动生成结构化风险报告。
3. trace 已新增 `risk_report_generated` 事件。
4. Flutter 已补齐“查看风险报告”入口和底部面板。
5. 后端与前端自动化验收均已通过。

### 收口判断
- 收口结论：`Closed`
- 下一活动阶段：`V5 / Phase-3`

## 6. V5 当前方向

- 治理层拒绝口径深化
- 风险报告质量增强与模板治理
- 报告历史中心/人工复核闭环能力
- 更细颗粒度的审计与报告追踪字段

### 当前已完成增量
1. 风险报告新增治理元数据：
   - `report_version`
   - `policy_version`
   - `generation_mode`
   - `source_stage`
   - `secondary_decision`
   - `risk_category`
   - `external_intelligence_level`
   - `trace_events`
2. 前端风险报告面板已新增治理上下文展示。
3. “我的”页风险报告中心已启动，当前仅展示高风险报告。
4. 已新增当前用户高风险报告列表接口，首版固定最近 20 条。
5. 已新增人工复核完整闭环：
   - 用户可从风险报告发起人工复核
   - “我的”页可查看复核单
   - 同 App 内置复核处理台可接单与关闭复核单
6. 已新增人工复核 API 与持久化状态机，复核结果只做治理记录，不回写业务裁决。
7. 已新增人工复核筛选与时间线追踪：
   - 用户侧复核单可按状态筛选
   - 处理台队列可按状态筛选
   - 复核详情页已展示提交、处理中、关闭时间线
8. 本轮自动化已通过：
   - 后端 `66 passed`
   - Flutter analyze `No issues found!`
   - Flutter widget test `All tests passed!`

## 7. 文档导航

- `README.md`：项目总入口与启动/验证说明
- `plan.md`：当前唯一执行计划
- `nowthink.md`：Ideal、完整架构、数据流、代码映射、最终指标
- `math.md`：公式、变量流、时延目标与风险报告后置说明
- `promode/`：执行约束与协作规则

---

更新日期：2026-04-09  
当前主版本：`V5 / Phase-3（进行中）`  
上一版本状态：`V4（已完成）`
