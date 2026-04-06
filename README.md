# Banking AI Demo Monorepo

基于 `Flutter + FastAPI + MCP + SQLite` 的手机银行风控演示项目。
当前 MVP 重点不是“聊天插件”，而是围绕转账场景打通 `风险分类 -> 预检决策 -> 二次质询 -> 最终确认/拦截` 的完整链路。

## 当前 MVP 能力

- 三态风控决策：`pass / interrogate / block`
- 风险分解落库：`flag_s`、`g_behavior`、`g_dynamic`、`final_risk`
- 风险知识库分类：基于常见金融诈骗/异常转账场景和关键词做匹配识别
- 二次拦截 Agent：结合知识库分类、对话内容和用户补充说明做二次放行判断
- 统一在线模型网关：后端通过 OpenAI 兼容接口调用模型，不再保留本地模板回答路径
- Flutter 演示页：账单改为弹窗展示，首页不再保留“最近交易”列表

## 项目结构

- `client_flutter/`：Flutter 客户端
- `server/`：FastAPI 后端、风险引擎、Agent 编排、SQLite 数据与测试
- `mcp_servers/`：银行 MCP Server
- `docs/`：架构说明、演示脚本、手工测试案例

## 快速启动

### 1. 启动后端

```powershell
py -3.13 -m venv server\.venv
server\.venv\Scripts\python -m pip install -r server\requirements.txt
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

### 2. 启动 Flutter

```powershell
cd client_flutter
```

Android 模拟器：

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Web：

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## 推荐演示路径

1. 打开首页，展示账户资产卡片和演示入口。
2. 点击 `转账`，输入低风险样例：收款人 `小b`、金额 `300`、城市 `上海`，验证 `pass`。
3. 点击 `风险演示`，触发中风险样例：收款人 `小c`、金额 `8000`、城市 `北京`。
4. 在二次质询弹窗中按提示填写关系、用途、是否涉及验证码/安全账户，观察二次放行或拦截结果。
5. 点击 `账单`，确认账单以弹窗方式展示。
6. 打开 `AI 助手`，可演示：
   - `帮我查一下余额`
   - `为什么刚才触发风控提醒`

更完整的人工测试触发方式见 `docs/risk-test-cases.md`。

## 已实现 API

- `GET /api/v1/dashboard`
- `GET /api/v1/transactions`
- `POST /api/v1/transfers/classify-risk`
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/agent/chat`

MCP 挂载路径：

- `/mcp/bank`

## 配置说明

参考根目录 `.env.example`：

- `APP_ENV`：运行环境
- `SQLITE_PATH`：SQLite 文件路径
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：主配置，按 OpenAI 兼容接口调用在线模型
- `LLM_API_NAME`：可选，请求透传字段
- `ARK_*` / `DEEPSEEK_*`：兼容旧配置的别名，建议逐步收敛到 `LLM_*`
- `MCP_BANK_ENABLED`：是否挂载银行 MCP 路由

说明：模型密钥只保留在后端配置中，Flutter 客户端不保存任何模型 Key。

## 测试命令

### 后端

```powershell
$env:PYTHONPATH=(Get-Location).Path
server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
```

### 前端

```powershell
cd client_flutter
flutter analyze --no-version-check
flutter test --no-version-check
```

## 当前约束

- 不再保留本地模板回答模式
- 系统仅保留银行风控主链路与银行 MCP
- 手工风险触发样例统一维护在 `docs/risk-test-cases.md`

## 参考文档

- 架构说明：`docs/architecture.md`
- 演示脚本：`docs/demo-script.md`
- 风控测试：`docs/risk-test-cases.md`
- 时序图：`docs/sequence-diagram.md`
