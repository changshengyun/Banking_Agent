# Banking AI Project Show Me

## 1. 项目一句话

这是一个面向手机银行客户端的 AI 风控演示系统，目标是把转账风控做成“可感知、可解释、可二次拦截、可审计”的完整闭环。

## 2. 当前 MVP 已实现什么

- Flutter 首页展示资产、账单入口、转账入口和 AI 助手
- 转账预检支持三态结果：`pass / interrogate / block`
- 风险分类已接入风险知识库，能按场景和关键词做初步识别
- 二次拦截支持标准化追问与用户补充说明
- Agent 聊天与二次校验都统一走 OpenAI 兼容模型接口
- MCP 当前只保留银行工具链：`/mcp/bank`

## 3. 代码结构怎么理解

### 前端

- `client_flutter/lib/main.dart`
  - 首页 UI
  - 转账弹窗
  - 账单弹窗
  - AI 助手弹窗
- `client_flutter/lib/banking_api.dart`
  - 封装所有 HTTP 请求
  - 负责 JSON 解析与异常处理

### 后端 API

- `server/app/api/routes/dashboard.py`
  - 首页与账单接口
- `server/app/api/routes/transfers.py`
  - 风险分类、预检、二次校验、确认转账
- `server/app/api/routes/agent.py`
  - AI 助手聊天接口

### 后端服务

- `server/app/services/bank_host.py`
  - 主编排服务
  - 聚合账户、账单、画像、历史交易与风控结果
- `server/app/services/risk_engine.py`
  - 规则与分值计算
- `server/app/services/risk_knowledge_base.py`
  - 风险场景库、关键词库、分类逻辑
- `server/app/services/agent_service.py`
  - 聊天编排
  - 二次拦截复核
- `server/app/services/llm_gateway.py`
  - 统一模型网关
  - 使用 `LLM_*` OpenAI 兼容字段调用在线模型

### 数据与工具层

- `server/app/repositories/banking.py`
  - 所有 SQLite 读写
- `mcp_servers/bank_server.py`
  - 银行 MCP 工具暴露层
- `server/app/mcp_runtime.py`
  - 把银行 MCP 挂载到 FastAPI

## 4. MCP 在项目里怎么落地

### 作用

MCP 的作用不是替代 REST，而是把银行能力做成标准化工具，方便 Agent 或外部系统复用。

### 当前工具

- `get_account_summary`
- `list_transactions`
- `get_user_profile`
- `get_static_profile`
- `get_common_locations`
- `classify_transfer_risk`
- `precheck_transfer_risk`
- `commit_transfer`

### 实现方式

1. `mcp_servers/bank_server.py` 通过 `@bank_mcp.tool()` 暴露工具。
2. 每个工具内部都复用 `BankHostService`，不重复写业务逻辑。
3. `server/app/mcp_runtime.py` 统一挂载到 `/mcp/bank`。

## 5. Agent 现在怎么工作

### 聊天 Agent

- 入口：`POST /api/v1/agent/chat`
- 代码主线：`AgentService.chat()`
- 做的事：
  - 记录用户消息
  - 读取账户、账单、最近风险摘要
  - 调用风险知识库做分类
  - 拼接上下文给 `LLMGateway`
  - 返回回答、工具痕迹和建议动作

### 二次拦截 Agent

- 入口：`POST /api/v1/transfers/secondary-check`
- 代码主线：`AgentService.evaluate_secondary_intercept()`
- 做的事：
  - 接收用户补充说明
  - 合并预检摘要、风险分类、命中关键词、追问点
  - 调用在线模型返回严格 JSON
  - 输出 `pass_secondary` 或 `block_secondary`

## 6. 风控主链路怎么走

1. 前端提交 `payee_name + amount + ClientContext`
2. 后端读取账户、常用城市、历史收款人、静态画像
3. 风险知识库先做场景分类
4. 风险引擎计算静态分、行为分、动态分、综合分
5. 返回 `pass / interrogate / block`
6. 若是 `interrogate`，前端弹出二次质询
7. 二次质询通过后，再调用确认转账

## 7. 现在怎么测

### 手工测试

- 主测试文档：`docs/risk-test-cases.md`
- 前端速查文档：`client_flutter/write.md`

### 自动化测试

```powershell
$env:PYTHONPATH=(Resolve-Path .).Path
server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
```

```powershell
cd client_flutter
flutter test --no-version-check
flutter analyze --no-version-check
```

## 8. 当前边界

- 不再保留 `MOCK_LLM` 或本地固定回答路径
- 不再保留户外知识模块
- 当前模型接入统一走后端 OpenAI 兼容接口
- 前端首页不展示最近交易，账单改为弹窗展示
