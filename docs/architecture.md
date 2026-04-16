# Banking AI Agent Demo Architecture

## 目标

项目当前围绕手机银行转账风控 MVP 建设，核心闭环是：

- 风险知识库完成常见金融风险场景分类
- 规则引擎完成 `pass / interrogate / block` 预检决策
- 二次质询 Agent 结合分类结果和用户补充说明判断是否继续放行
- 所有在线模型统一走 OpenAI 兼容接口，不再保留本地模板模式

## 主要组件

### `client_flutter/`

- 展示账户资产、转账入口、账单弹窗、AI 助手弹窗
- 采集 `ClientContext`，包括城市、页面、动作、语义摘要、输入停顿、输入时长等行为信号
- 调用 FastAPI，不直接调用模型 API

### `server/`

- `api/routes/`：只负责收参与返回
- `services/bank_host.py`：聚合账户、交易、风险引擎、待确认转账与 Agent 能力
- `services/risk_engine.py`：静态分、行为分、动态分融合，输出三态决策
- `services/risk_knowledge_base.py`：常见诈骗/异常转账场景知识库与关键词匹配
- `services/agent_service.py`：聊天编排、二次质询结果判定
- `services/llm_gateway.py`：统一 OpenAI 兼容模型网关
- `repositories/`：SQLite 数据读写

### `mcp_servers/`

- `bank_server.py`：提供账户摘要、交易列表、静态画像、风险分类、风险预检、确认转账等工具

## 核心链路

### 1. 风险分类与预检

1. Flutter 提交 `payee_name`、`amount`、`ClientContext` 到 `/api/v1/transfers/precheck`。
2. `BankHostService` 读取账户、历史收款人、常用城市、静态画像。
3. `RiskKnowledgeBaseService` 先做场景分类与关键词命中。
4. `RiskEngine` 融合静态特征、行为特征、语义风险，输出 `pass / interrogate / block`。
5. 结果写入 `pending_transfers` 和 `risk_events`，供后续确认与解释复用。

### 2. 二次质询

1. 当前决策为 `interrogate` 时，前端展示标准化补充问题和回答样例。
2. 用户提交补充说明到 `/api/v1/transfers/secondary-check`。
3. `AgentService.evaluate_secondary_intercept()` 将原始语义摘要、风险分类、命中关键词、追问点和用户回答交给 `LLMGateway`。
4. 模型返回严格 JSON：`pass_secondary` 或 `block_secondary`，以及原因和用户提示。

### 3. AI 助手

1. Flutter 将聊天消息和 `ClientContext` 提交到 `/api/v1/agent/chat`。
2. `AgentService.chat()` 聚合账户摘要、账单摘要、最近风控事件和知识库分类结果。
3. `LLMGateway` 调用在线模型生成结构化回复。
4. 返回 `assistant_message`、`used_tools`、`suggested_actions`。

## MCP 工具映射

- `get_account_summary`
- `list_transactions`
- `get_user_profile`
- `get_static_profile`
- `get_common_locations`
- `classify_transfer_risk`
- `precheck_transfer_risk`
- `commit_transfer`

## 当前实现边界

- 当前只保留银行 MCP 主链路
- 当前不再提供本地模板回答切换
- 当前风险场景知识库为轻量内置版本，后续可替换为真正的向量数据库或检索服务
