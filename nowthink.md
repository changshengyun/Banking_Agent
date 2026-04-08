# nowthink · Ideal、架构、数据流与实现映射

> 本文档只回答四件事：系统理想形态是什么、数据如何流动、当前代码如何映射、最终性能指标是什么。  
> 不承担当前执行排期职责，当前执行顺序以 `plan.md` 为准。

## 1. 项目 Ideal

系统目标不是“看见关键词就拦截”，而是构建一个金融级的 HIRD 风控大脑：
- 感知层拿到真实上下文和行为脉冲
- 认知层用多 Agent 判断“用户为什么这样做”
- 治理层把不确定的 AI 建议压缩成可验证的确定性决策
- 执行层把决策变成明确业务动作和审计事件

核心设计原则：
- Agent 只负责分析，不负责执行业务动作
- 治理层保留最终裁决权
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
  - 外部情报
- 当前代码映射：
  - `server/app/schemas/common.py`
  - `server/app/services/external_intelligence.py`
  - `server/app/repositories/banking.py`

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
- 核心职责：
  - 公式计算
  - 阈值路由
  - 状态机控制
  - 拒绝分支口径统一
  - Trace 审计沉淀

### HIRD-E 业务执行层
- 当前代码映射：
  - `server/app/api/routes/transfers.py`
  - `server/app/services/bank_host.py`
  - `client_flutter/lib/main.dart`
- 当前动作：
  - `confirm`
  - `cancel`
  - `secondary-check`
  - explain pack 展示

## 3. 数据如何流动

### 3.1 预检路径
1. 前端提交 `TransferPrecheckRequest`
2. `BankHostService.precheck_transfer()` 聚合上下文与外部情报
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
2. `BankHostService.secondary_check_transfer()` 先校验 token 状态
3. `AgentService.evaluate_secondary_intercept()` 按顺序执行：
   - 红旗规则直拦
   - 本地低风险放行
   - 无关回复拒绝
   - LLM 兜底
4. 治理层回写：
   - `pending_transfers.secondary_*`
   - `risk_events`
   - `trace_events`
5. 前端收到：
   - `secondary_decision`
   - `semantic_red_flags`
   - `final_risk_after_secondary`
   - `explain_pack`

### 3.3 确认与取消路径
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
  - 装配知识库、风险引擎、外部情报、仓储
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

### 持久化与审计
- `server/app/repositories/banking.py`
  - `pending_transfers`
  - `risk_events`
  - `trace_events`
- `mcp_servers/bank_server.py`
  - 当前已暴露银行演示工具
  - V3-beta 继续承接审计查询工具

## 5. 为什么当前不把 precheck 全走 Agent

当前 `secondary-check` 的 LLM 路径使用同步 `httpx.Client`，默认超时 `2.0s`。  
如果把 `precheck` 也切成 mandatory Agent，会把外部模型调用放进热路径，直接恶化以下三项：
- `precheck` 稳定时延
- 模型不可用时的主链路可用性
- 决策一致性与可复核性

所以当前策略固定为：
- `precheck`：知识库 + 规则引擎
- `secondary-check`：规则优先 + Agent 兜底
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

### UX 配套要求
- `>1s` 显示 loading/busy 状态
- `>10s` 显示明确等待反馈，并允许用户中断或取消

## 7. 最终演进方向

- V3-beta：统一取消链路 + Trace 审计入 MCP
- V4：补齐 MCP 感知层的全部能力
- V5：补齐治理层并落地初版风险报告 Agent

---

更新日期：2026-04-08  
定位：`架构与数据流文档`
