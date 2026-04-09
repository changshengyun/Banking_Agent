# nowthink · Ideal、架构、数据流与实现映射

> 本文档只回答四件事：系统理想形态是什么、数据如何流动、当前代码如何映射、最终性能指标是什么。  
> 不承担当前执行排期职责，当前执行顺序以 `plan.md` 为准。

## 1. 项目 Ideal

系统目标不是“看见关键词就拦截”，而是构建一个金融级的 HIRD 风控大脑：
- 感知层拿到真实上下文和行为脉冲
- 认知层用多 Agent 判断“用户为什么这样做”
- 治理层把不确定的 AI 建议压缩成可验证的确定性决策
- 执行层把决策变成明确业务动作和审计事件
- 报告层在裁决之后生成可读、可复核、可持久化的风险说明

核心设计原则：
- Agent 只负责分析，不负责执行业务动作
- 治理层保留最终裁决权
- 风险报告 Agent 只做说明，不改变裁决
- 审计链路独立，不能被 LLM 调用成败绑架
- 所有业务状态变更都必须可追溯

## 2. HIRD 四层架构

### HIRD-H 感知集成层
- 输入：
  - `ClientContext`
  - 收款人
  - 金额
  - 城市
  - 页面与行为信号
  - 输入微行为
  - 外部情报
- 当前代码映射：
  - `server/app/schemas/common.py`
  - `server/app/services/external_intelligence.py`
  - `server/app/repositories/banking.py`
  - `server/app/services/bank_host.py::_build_perception_snapshot`
- 当前职责：
  - 将设备、位置、页面行为、输入行为、语义摘要、外部情报压缩为统一的 `perception_snapshot`

### HIRD-C/R 认知决策层
- 角色：
  - 领域初分
  - 领域细分
  - 语义分析
- 当前代码映射：
  - `server/app/services/risk_knowledge_base.py`
  - `server/app/services/agent_service.py`
  - `server/app/services/embedding_service.py`
- 输出：
  - `risk_category`
  - `c_match`
  - `semantic_red_flags`
  - `secondary_risk`

### HIRD-G 治理控制层
- 当前代码映射：
  - `server/app/services/risk_engine.py`
  - `server/app/services/pii_masker.py`
  - `server/app/services/bank_host.py`
  - `server/app/services/risk_report_service.py`
- 核心职责：
  - 公式计算
  - 阈值路由
  - 状态机控制
  - 拒绝分支口径统一
  - 风险报告触发与持久化
  - Trace 审计沉淀

### HIRD-E 业务执行层
- 当前代码映射：
  - `server/app/api/routes/transfers.py`
  - `client_flutter/lib/banking_api.dart`
  - `client_flutter/lib/main.dart`
- 当前动作：
  - `confirm`
  - `cancel`
  - `secondary-check`
  - `risk-report view`
  - explain pack 展示

## 3. 数据如何流动

### 3.1 预检路径
1. 前端提交 `TransferPrecheckRequest`
2. `BankHostService.precheck_transfer()` 聚合上下文、外部情报与感知快照
3. `RiskKnowledgeBase.classify_text()` 产出：
   - `risk_category`
   - `risk_level`
   - `matched_keywords`
   - `matched_scenarios`
   - `c_match` 的上游信号
4. `RiskEngine.assess()` 产出：
   - `flag_s`
   - `g_behavior`
   - `g_dynamic`
   - `final_risk`
   - `decision`
5. `BankHostService` 写入：
   - `pending_transfers`
   - `risk_events`
   - `trace_events`
6. 前端收到：
   - `decision`
   - `risk_classification`
   - `external_intelligence`
   - `explain_pack`

### 3.2 二次质询路径
1. 前端提交 `TransferSecondaryCheckRequest`
2. `BankHostService.secondary_check_transfer()` 校验 token 状态
3. `AgentService.evaluate_secondary_intercept()` 按顺序执行：
   - 红旗规则直拦
   - 本地低风险放行
   - 无关回复拒绝
   - LLM 兜底
4. 治理层回写：
   - `pending_transfers.secondary_*`
   - `risk_events`
   - `trace_events.secondary_decided`
5. 在 `secondary-check` 结果确定后，`RiskReportService` 基于用户画像、文本、风险分类、语义红旗、外部情报和 explain pack 生成结构化报告
6. 报告写入：
   - `risk_reports`
   - `trace_events.risk_report_generated`
7. 前端收到：
   - `secondary_decision`
   - `semantic_red_flags`
   - `final_risk_after_secondary`
   - `explain_pack`

### 3.3 风险报告查看路径
1. Flutter 在二次校验完成后调用 `GET /api/v1/transfers/{confirmation_token}/risk-report`
2. 后端从 `risk_reports` 读取结构化报告
3. 前端用底部面板展示：
   - `headline`
   - `overall_risk_level`
   - `risk_summary`
   - `risk_factors`
   - `recommended_action`
   - `evidence`
   - `generated_at`

### 3.4 确认与取消路径
- `confirm`
  - 只允许 `pending`
  - `interrogate` 路径必须先得到 `pass_secondary`
  - 成功后写 `transactions`，并写 `trace_events.transfer_confirmed`
- `cancel`
  - 只允许 `pending -> cancelled`
  - 取消后再次 `confirm / secondary-check / cancel` 都进入拒绝分支
  - 审计中记录取消发生阶段：
    - `after_precheck`
    - `after_secondary_check`

## 4. 当前代码如何实现

### 核心服务
- `server/app/services/bank_host.py`
  - 业务编排入口
  - 装配知识库、风险引擎、外部情报、仓储、报告服务
- `server/app/services/risk_engine.py`
  - 主公式
  - 阈值路由
  - 行为脉冲建模
- `server/app/services/risk_knowledge_base.py`
  - 向量召回
  - 关键词/高危短语
  - 否定语义识别
- `server/app/services/agent_service.py`
  - 二次质询语义分析
  - 红旗阻断
  - 本地低风险放行
  - LLM 兜底
- `server/app/services/risk_report_service.py`
  - 结构化风险报告生成
  - LLM JSON 优先
  - fallback 兜底

### 持久化与审计
- `server/app/repositories/banking.py`
  - `pending_transfers`
  - `risk_events`
  - `trace_events`
  - `risk_reports`
- `server/app/schemas/report.py`
  - 风险报告结构化 schema
- `mcp_servers/bank_server.py`
  - 当前继续承接审计查询工具
  - 风险报告暂未作为 MCP 独立工具暴露

### 前端映射
- `client_flutter/lib/banking_api.dart`
  - 新增 `fetchRiskReport()`
- `client_flutter/lib/main.dart`
  - 二次校验后加载报告
  - `_RiskReportSheet` 展示结构化摘要

## 5. 为什么当前不把 precheck 全走 Agent

当前 `secondary-check` 的 LLM 路径使用同步 `httpx.Client`，默认超时 `2.0s`。  
如果把 `precheck` 也切成 mandatory Agent，会把外部模型调用放进热路径，直接恶化以下三项：
- `precheck` 稳定时延
- 模型不可用时的主链路可用性
- 决策一致性与可复核性

所以当前策略固定为：
- `precheck`：知识库 + 规则引擎
- `secondary-check`：规则优先 + Agent 兜底
- `risk report`：`secondary-check` 后的说明性产物
- `precheck all-Agent`：只允许 shadow mode 评估，不进入主路径

## 6. 最终目标性能指标

### 当前 demo 目标值
- `precheck hot path <= 750ms`
- `deterministic risk decision subpath <= 300ms`
- `secondary-check avg <= 3s`
- `LLM path P95 <= 30s`

### 这些目标怎么来的
- `precheck hot path <= 750ms`
  - 来自公开实时支付欺诈决策 `under 250 milliseconds` 的 3 倍 demo 放宽口径
- `deterministic risk decision subpath <= 300ms`
  - 来自公开授权风险评分 `under 100 ms` 的 3 倍 demo 放宽口径
- `secondary-check avg <= 3s`
  - 来自 NN/g 对“用户思路不中断”的 `1 second` 响应阈值，放宽 3 倍
- `LLM path P95 <= 30s`
  - 来自 NN/g 对“注意力保持”的 `10 seconds` 上限，放宽 3 倍

### V4 收口验证状态
- `V4` 自动化验收已通过：
  - 后端：`58 passed`
  - Flutter analyze：`No issues found!`
  - Flutter widget test：`All tests passed!`
- 之前的 Flutter 超时并非代码根因，而是环境问题，当前已排除。
- 性能仍持续观测，但不是 `V4` 完成的阻塞项。

## 7. 最终演进方向

- `V4`：感知层 + 初版风险报告 Agent 双主线，已完成
- `V5`：治理深化 + 报告增强，当前活动阶段

---

更新日期：2026-04-09  
定位：`架构与数据流文档`
