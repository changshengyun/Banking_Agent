# Banking AI Demo Monorepo

基于 `Flutter + FastAPI + MCP + SQLite + OpenAI 兼容接口` 的手机银行全链路风控演示项目。
当前开发主线围绕转账场景，按 `风险分类 -> 预检决策 -> 二次质询 -> 最终确认/拦截` 的 MVP 路径持续推进。

## 当前版本能力

- 三态风控决策：`pass / interrogate / block`
- 风险评分主链路：`flag_s`、`g_behavior`、`g_dynamic`、`final_risk`
- 风险知识库分类：基于常见金融诈骗/异常转账场景与关键词做匹配识别
- `V2-patch-1`：扩展投资理财诈骗、情感诈骗、刷单兼职诈骗，并输出 `high_risk_phrase_hits`
- `V2-patch-2`：二次质询主问题按风险场景动态选择，并把强制核验点注入 Agent 提示词
- `V2-patch-3`：新增语义红旗直拦规则与无关回复识别，二次质询响应新增 `semantic_red_flags`
- 统一在线模型网关：后端通过 OpenAI 兼容接口调用模型，不再保留本地 Mock LLM 路径
- `explain_pack` 解释包：预检与二次质询响应统一返回 XAI 面板数据
- `external_intelligence` 外部情报：预检与二次质询统一返回名单筛查结果
- Flutter 演示端：账单改为弹窗展示，首页不再展示“最近交易”列表

## V2-patch-3 重点说明

`V2-patch-3` 聚焦“二次拦截更像真实银行风控复核”这一目标，当前已实现：

- 本地确定性红旗规则：命中“司法机关要求转账”“安全账户/资金清查”“客服要求验证资金”“验证码/屏幕共享”“投资收益诱导”等语义时直接阻断
- 无关回复识别：用户若只回复“我就是想转账”“别问了”这类回避性内容，不允许直接放行，至少进入 `interrogate`
- LLM 输出兜底校验：若模型返回了 `semantic_red_flags` 但未选择 `block_secondary`，后端会强制修正为阻断结果
- API 契约补充：`POST /api/v1/transfers/secondary-check` 响应新增 `semantic_red_flags`

## 项目结构

- `client_flutter/`：Flutter 客户端
- `server/`：FastAPI 后端、风控引擎、Agent 编排、SQLite 数据与测试
- `mcp_servers/`：银行 MCP Server
- `docs/`：架构说明、演示脚本、手工测试样例
- `skill/`：多 Agent 协作开发使用的本地技能说明

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

1. 打开首页，确认资产卡片和风控演示入口正常显示。
2. 进入 `转账`，输入低风险样例：收款人 `小A`、金额 `300`、城市 `上海`，验证 `pass` 路径。
3. 触发中高风险样例：收款人 `小B`、金额 `8000`、城市 `北京`，观察预检结果与解释包。
4. 在二次质询弹窗中输入高风险说明，例如“警察让我转的”“客服让我先验证资金后退款”，观察 `block_secondary` 和 `semantic_red_flags`。
5. 在二次质询弹窗中输入无关回复，例如“我就是想转账，别问了”，观察系统不会直接放行。
6. 点击 `账单`，确认账单以弹窗形式展示。
7. 打开 `AI 助手`，验证余额查询、最近风控事件说明等能力。

更完整的手工测试样例见 [docs/risk-test-cases.md](e:/Projects/Banking_AI_Project/docs/risk-test-cases.md)。

## 已实现 API

- `GET /api/v1/dashboard`
- `GET /api/v1/transactions`
- `POST /api/v1/transfers/classify-risk`
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/agent/chat`

接口说明：

- `precheck` 与 `secondary-check` 当前都返回结构化 `explain_pack`
- `precheck` 与 `secondary-check` 当前都返回 `external_intelligence`
- `secondary-check` 当前额外返回 `semantic_red_flags`
- `explain_pack.nodes` 当前固定包含 `static`、`behavior`、`semantic`、`external_intelligence`、`decision`

MCP 路径：

- `/mcp/bank`
- MCP 已挂载 `screen_external_intelligence` 工具，用于独立筛查收款人外部名单命中

## 配置说明

参考根目录 `.env.example`：

- `APP_ENV`：运行环境
- `SQLITE_PATH`：SQLite 文件路径
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：在线模型主配置，按 OpenAI 兼容接口调用
- `LLM_API_NAME`：可选，请求透传字段
- `ARK_*` / `DEEPSEEK_*`：兼容历史配置的别名，建议逐步收敛到 `LLM_*`
- `MCP_BANK_ENABLED`：是否挂载银行 MCP 路由

说明：模型密钥仅保留在后端配置中，Flutter 客户端不保存任何模型 Key。

## 测试命令

### 后端

```powershell
$env:PYTHONPATH=(Get-Location).Path
server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_patch2_secondary_followup.py -q -p no:cacheprovider
```

### 前端

```powershell
cd client_flutter
flutter analyze --no-version-check
flutter test --no-version-check
```

## 当前验证结果

- `V2-patch-1 / V2-patch-2 / V2-patch-3`：已全部完成，当前进入 V2 收口提交阶段
- `server/tests/test_api.py`：14 通过
- `server/tests/test_risk_scenarios.py`：13 通过
- `server/tests/test_patch2_secondary_followup.py`：2 通过
- `flutter analyze --no-version-check`：通过
- `flutter test --no-version-check`：6 通过
- `V2-patch-3` 已验证：
  - 命中高风险语义时直接 `block_secondary`
  - 无关回复不会被直接 `pass_secondary`
  - `semantic_red_flags` 字段稳定返回

## 开发治理

- 路线图与阶段汇总：`MVP.md`
- 当前执行流与多 Agent 分工：`work_now.md`
- 多 Agent 角色技能：
  - `skill/project-manager/SKILL.md`
  - `skill/architect/SKILL.md`
  - `skill/engineer/SKILL.md`
- 固定规则：
  1. 按 `MVP V1 -> V2 -> V3 -> V4` 顺序开发。
  2. 每次实际代码改动都要同步更新根目录 `README.md`。
  3. 每完成一个可审阅 MVP 补丁，都要先更新 `MVP.md` / `Showme_func.md`，再执行 Git 提交与推送。

## 当前约束

- 不再保留本地 LLM Mock 回答模式
- 系统仅保留银行风控主链路与银行 MCP
- 手工风险触发样例统一维护在 `docs/risk-test-cases.md`

## 参考文档

- `docs/architecture.md`
- `docs/demo-script.md`
- `docs/risk-test-cases.md`
- `docs/sequence-diagram.md`
