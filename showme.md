# Banking AI Project Show Me

## 1. 给领导的总览（先看这个）

这是一个 **演示优先** 的银行 App 原型系统，核心目标有两件事：

1. 前后端 + MCP 架构闭环（能跑、能演示、能联调）  
2. 转账场景下的 AI 风控能力（可解释、可确认、可追溯）

技术分层：

- 前端：Flutter（页面、交互、上下文采集）
- 后端：FastAPI（Host 编排、风控、聊天、统一 API）
- 数据：SQLite（演示数据 + 事件记录）
- MCP：bank/outdoor 两个 MCP Server（工具化能力对外暴露）

---

## 2. 架构图（代码层面）

```text
Flutter App
  ├─ 调 REST API (/api/v1/*)
  └─ 采集 ClientContext（城市、设备、页面、语义摘要）
        ↓
FastAPI (server/app/main.py)
  ├─ API Router (dashboard/transfers/agent)
  ├─ Host Service (BankHostService)
  ├─ Agent Service (mock or online llm)
  ├─ Risk Engine (规则决策)
  ├─ Repository (SQL读写)
  └─ MCP Runtime (挂载 /mcp/bank, /mcp/outdoor)
        ↓
SQLite + MCP tools
```

---

## 3. 每个核心文件的用处（按目录）

### 3.1 server/app（后端主工程）

- `server/app/main.py`  
  应用入口。启动时初始化数据库、种子数据、挂载 MCP；注册 CORS、异常处理、根健康接口。

- `server/app/config.py`  
  统一读取配置（`.env`、环境变量），包括模型参数、MCP 开关、SQLite 路径。支持 `LLM_*` 与 `ARK_*` 别名。

- `server/app/db.py`  
  数据库 schema 定义 + 连接上下文管理。包含用户、账户、交易、收款人、地点画像、风控事件、待确认转账、会话消息等表。

- `server/app/seed.py`  
  演示数据灌入（含兼容迁移逻辑），保证每次启动都可演示。

- `server/app/mcp_runtime.py`  
  将 MCP Server 挂载到 FastAPI：`/mcp/bank`、`/mcp/outdoor`。

### 3.2 server/app/api（接口层）

- `server/app/api/router.py`  
  统一前缀 `/api/v1`，组合 dashboard/transfers/agent 路由。

- `server/app/api/routes/dashboard.py`  
  首页接口：`GET /dashboard`、`GET /transactions`。

- `server/app/api/routes/transfers.py`  
  转账接口：`POST /transfers/precheck`、`POST /transfers/confirm`。

- `server/app/api/routes/agent.py`  
  聊天接口：`POST /agent/chat`。

### 3.3 server/app/services（业务层）

- `server/app/services/bank_host.py`  
  后端“主编排器”：首页聚合、转账预检、确认转账、风险解释、账单摘要。  
  是 REST 和 MCP 共用的核心业务服务。

- `server/app/services/risk_engine.py`  
  规则引擎：非常用地点、大额、首次收款人、短时连续操作 -> 输出 `pass/review` + 风险等级 + 原因。

- `server/app/services/agent_service.py`  
  聊天编排：  
  - `MOCK_LLM=true` 走模板化回复  
  - `MOCK_LLM=false` 走在线模型（方舟 OpenAI 兼容）  
  并记录聊天会话、返回工具痕迹和建议动作。

- `server/app/services/outdoor_knowledge.py`  
  轻量户外知识库（演示多工具接入，不进入转账主链路）。

### 3.4 server/app/repositories（数据访问层）

- `server/app/repositories/banking.py`  
  所有 SQL 读写集中在这里：账户、交易、地点画像、收款人、风险事件、待确认转账、聊天记录。

### 3.5 server/app/schemas（数据契约层）

- `server/app/schemas/common.py`  
  定义 `ClientContext`、交易项、工具使用、建议动作、决策类型。

- `server/app/schemas/dashboard.py`  
  首页/交易返回结构。

- `server/app/schemas/transfer.py`  
  转账预检/确认请求与响应结构。

- `server/app/schemas/chat.py`  
  聊天请求与响应结构。

### 3.6 mcp_servers（MCP 工具层）

- `mcp_servers/bank_server.py`  
  银行 MCP 工具：  
  `get_account_summary`、`list_transactions`、`get_user_profile`、`get_common_locations`、`precheck_transfer_risk`、`commit_transfer`。

### 3.7 client_flutter（前端）

- `client_flutter/lib/main.dart`  
  页面主逻辑：首页加载、转账弹层、风险确认弹窗、AI 聊天面板。

- `client_flutter/lib/banking_api.dart`  
  HTTP 客户端封装：所有 API 调用、JSON 解析、异常处理（`ApiException`）。

---

## 4. MCP 的用处、如何调用、代码如何实现

## 4.1 MCP 的价值（业务价值）

MCP 的核心价值是：**把能力做成标准工具接口**，让 Agent/系统在统一协议下可插拔调用。  
在这个项目里：

- 银行业务能力做成 MCP 工具（查余额、查流水、预检风控、确认转账）
- 户外知识也做成 MCP 工具（演示多工具接入能力）

这样后续可以：

- 让不同 Agent 客户端复用工具
- 把银行能力和聊天能力“解耦”
- 扩展新工具不影响主业务 API

## 4.2 当前代码里的实现方式

1. 定义工具（Tool）  
   在 `mcp_servers/bank_server.py` 和 `mcp_servers/outdoor_server.py` 用 `@xxx_mcp.tool()` 声明。

2. 挂载到服务  
   `server/app/mcp_runtime.py` 在 FastAPI 内挂载：
   - `/mcp/bank`
   - `/mcp/outdoor`

3. 复用同一业务核心  
   MCP 工具内部不是单独写一套逻辑，而是直接调 `BankHostService`。  
   这保证 REST 与 MCP 的业务结果一致。

## 4.3 调用关系（很关键）

目前主链路是：

- Flutter 调 REST API（`/api/v1/*`）  
- FastAPI 内部通过 `BankHostService` 完成风控与业务处理
- MCP 工具作为“并行能力入口”已经挂好，供外部 Agent 或后续联动使用

也就是说：**MCP 已实现并可调用，但前端主流程默认仍走 REST。**

---

## 5. “多模态数据如何标准化”——当前做法与改造方向

## 5.1 当前项目已做的“标准化基础”

虽然当前不是真正图像/语音多模态，但已经有统一上下文容器：

- `ClientContext`（`session_id/device_id/platform/current_city/lat/lng/recent_page/last_action/semantic_summary`）
- 前端统一通过 `ClientContextData.toJson()` 上送
- 后端用 Pydantic schema 强校验并转结构体

这相当于先把“行为上下文 + 语义摘要”标准化了。

## 5.2 真正多模态该怎么标准化（建议）

建议新增统一结构 `MultimodalEvidence`：

- `modality`: `text | image | audio | video | location | device`
- `timestamp`
- `source`: `camera/mic/gps/ui_action/...`
- `raw_uri`: 对象存储地址或文件 ID
- `features`: 标准特征（如 embedding、ASR 文本、OCR 文本、声纹分数、图像风险标签）
- `quality_score` / `integrity_hash`

然后做“适配器层”：

- 图像适配器 -> OCR/目标识别 -> 标准 features
- 音频适配器 -> ASR/声纹 -> 标准 features
- 位置适配器 -> 轨迹可信度 -> 标准 features

最后统一入风控特征面板，再由规则 + 模型联合判断。

---

## 6. API 如何调用并处理数据（联动说明）

## 6.1 首页链路

1. Flutter `main.dart` 启动后调用 `fetchDashboard()`  
2. `banking_api.dart` 请求 `GET /api/v1/dashboard`  
3. 路由进入 `dashboard.py`  
4. `BankHostService.get_dashboard()` 聚合账户+交易+摘要  
5. 返回 JSON，前端解析为 `DashboardData` 展示

## 6.2 转账风控链路

1. 前端提交 `payee_name + amount + ClientContext` 到 `/transfers/precheck`  
2. `BankHostService.precheck_transfer()` 拉历史数据、调用 `RiskEngine.assess()`  
3. 写 `pending_transfers` + `risk_events`  
4. 返回 `decision/risk_level/reasons/confirmation_token`  
5. 若前端确认，再调 `/transfers/confirm`，完成扣款、写流水、更新收款人

## 6.3 AI 聊天链路

1. 前端调 `/agent/chat`（带消息 + `ClientContext`）  
2. `AgentService.chat()` 先记 user 消息  
3. 按配置走 mock 或在线模型  
4. 在线模型会注入账户、账单、风控上下文构建 prompt  
5. 记录 assistant 消息并返回 `assistant_message + used_tools + suggested_actions`

---

## 7. 各函数间联动（你可直接对外讲）

可以把系统理解为 5 层流水线：

1. `main.dart / banking_api.dart`：采集并发送请求  
2. `api/routes/*.py`：路由分发  
3. `services/*.py`：业务编排（风控、聊天）  
4. `repositories/banking.py`：数据库读写  
5. `db.py + SQLite`：持久化

MCP 是旁路“工具化接口层”，复用第 3 层业务能力。

---

## 8. 如果要加“多模态转账风控 Agent”，我会这样做

### 阶段 A：先打地基（1-2 天）

1. 新增 schema：`MultimodalEvidence`、`RiskFeatureVector`  
2. 新增表：`evidences`、`risk_feature_snapshots`、`risk_decision_logs`  
3. 扩展 `TransferPrecheckRequest` 支持 `evidences[]`

### 阶段 B：接入与标准化（2-3 天）

1. 新增 `services/multimodal_adapter.py`  
2. 实现 text/image/audio/location 的 feature 提取适配接口  
3. 输出统一 `RiskFeatureVector`（字段固定、可审计）

### 阶段 C：决策与解释（2-3 天）

1. `RiskEngine` 升级为“规则 + 模型评分”双轨  
2. 保留规则兜底（演示稳定），模型只做增益  
3. `AgentService` 输出“哪些模态证据触发了风险”的解释文本

### 阶段 D：MCP 工具升级（1-2 天）

新增 MCP 工具：

- `ingest_multimodal_evidence`
- `extract_risk_features`
- `precheck_transfer_risk_v2`
- `explain_risk_decision`

并挂到 `/mcp/bank`，让外部 Agent 可直接按 MCP 调用。

### 阶段 E：前端联动（1-2 天）

1. 转账页增加可选拍照/语音备注/定位可信度  
2. 上送 `evidences[]`  
3. 风控弹窗展示“证据来源 + 置信度 + 处置建议”

---

## 9. 我作为技术负责人会强调的三点

1. 风控决策必须可解释、可追溯、可回放（你答辩最加分）  
2. 多模态引入后先做“标准化和审计链路”，再谈模型精度  
3. 任何模型判断都要有规则兜底，保证演示与生产都稳

