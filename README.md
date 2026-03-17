# Banking AI Demo Monorepo

基于 `Flutter + FastAPI + MCP + SQLite` 的银行 AI Agent 演示项目。  
项目定位是“答辩/演示优先”，重点展示：

- AI Agent 风控提醒与二次确认流程
- 前后端分层架构（Flutter 客户端 + FastAPI 主编排）
- MCP 工具化能力（银行工具 + 户外知识工具）

## 1. 项目结构

- `client_flutter/`：Flutter 客户端（已包含 `android/` 平台目录）
- `server/`：FastAPI 后端、SQLite 数据、Agent 编排与测试
- `mcp_servers/`：MCP Server（bank / outdoor）
- `docs/`：架构说明与演示脚本

## 2. 环境要求

- Windows PowerShell（示例命令按 Windows 写）
- Python `3.13`
- Flutter SDK（建议已配置到 PATH）
- Android Studio / Android SDK（若要跑 Android 模拟器）

## 3. 快速启动（推荐）

### 3.1 后端启动

在项目根目录执行：

```powershell
py -3.13 -m venv server\.venv
server\.venv\Scripts\python -m pip install -r server\requirements.txt
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后可访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

### 3.2 前端启动

新开一个终端，进入 Flutter 目录：

```powershell
cd client_flutter
```

#### Android 模拟器/真机

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

#### Web（Chrome）

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## 4. 演示流程（建议答辩顺序）

1. 打开首页，展示后端返回的资产和最近交易。
2. 点击 `风险演示`（预置：收款人 `小c`、金额 `8000`、城市 `北京`）。
3. 提交预检，展示风险提醒弹窗（`review/high`）。
4. 点击继续确认，展示转账成功和余额更新。
5. 打开 `AI 助手`，可演示以下问题：
   - `帮我查一下余额`
   - `为什么刚才触发风控提醒`
   - `给我一条露营安全建议`

## 5. API 清单（当前已实现）

- `GET /api/v1/dashboard`
- `GET /api/v1/transactions`
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/agent/chat`

MCP 挂载路径：

- `/mcp/bank`
- `/mcp/outdoor`

## 6. 配置说明

根目录可参考 `.env.example`：

- `APP_ENV`：运行环境
- `SQLITE_PATH`：SQLite 文件路径
- `MOCK_LLM`：默认 `false`（在线模型模式），如需离线演示可手动设为 `true`
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：默认按豆包（火山方舟）OpenAI 兼容参数读取
- `ARK_API_KEY` / `ARK_BASE_URL` / `ARK_MODEL` / `ARK_API_NAME`：`LLM_*` 的别名
- `MCP_BANK_ENABLED` / `MCP_OUTDOOR_ENABLED`：是否挂载 MCP 路由

说明：后端会自动读取根目录 `.env`（以及 `server/.env`），模型 Key 仅保留在后端配置中。

## 7. 测试与质量检查

### 后端测试

```powershell
server\.venv\Scripts\python -m pytest server\tests -q -p no:cacheprovider
```

### 前端测试

```powershell
cd client_flutter
flutter test --no-version-check
flutter analyze --no-version-check
```

## 8. 常见问题

- `前端提示无法连接后端`
  - 确认后端是否已在 `127.0.0.1:8000` 启动
  - Android 模拟器请使用 `10.0.2.2` 访问宿主机

- `Android 无法运行`
  - 先执行 `flutter doctor`，补齐 Android toolchain/JDK/SDK
  - 确认设备可见：`flutter devices`

- `想接入真实模型`
  - 设置 `MOCK_LLM=false`
  - 配置后端的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`
  - 不要在 Flutter 客户端中放模型密钥

## 9. 参考文档

- 架构说明：`docs/architecture.md`
- 演示脚本：`docs/demo-script.md`
- 时序图：`docs/sequence-diagram.md`
