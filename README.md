# Banking AI Demo Monorepo

基于 `Flutter + FastAPI + MCP + SQLite + OpenAI-compatible LLM` 的手机银行风控演示项目。  
当前执行阶段为 `V4 / Phase-1（感知层能力建设）`，`V3-beta` 已收口完成。

## 当前能力

- 三态预检决策：`pass / interrogate / block`
- 单轮二次质询：`pass_secondary / interrogate / block_secondary`
- 显式取消交易：`POST /api/v1/transfers/cancel`
- explain pack：结构化解释面板
- 三类 Agent：领域初分、领域细分、语义分析
- 审计链路：`trace_events` + MCP 查询

## 文档导航

- `README.md`
  - 项目总入口、启动方法、验证命令
- `MVP.md`
  - 版本台账、完整度评估、路线图
- `plan.md`
  - 当前唯一执行计划
- `nowthink.md`
  - Ideal、完整架构、数据流、代码映射、最终指标
- `math.md`
  - 公式、变量流、场景算例、时延目标推导
- `promode/codex_execution_rules.md`
  - Codex 固定执行规则正文
- `promode/development_requirements_summary.md`
  - 你历史开发要求的统一汇总入口

## 风控主链路

1. 前端发起 `precheck`
2. 后端聚合 `ClientContext`、知识库分类、外部情报
3. `RiskEngine` 计算 `flag_s / g_behavior / g_dynamic / final_risk`
4. 若为 `interrogate`，进入 `secondary-check`
5. `AgentService` 做二次质询语义分析
6. 最终进入 `confirm / cancel / block`
7. 关键节点写入 `trace_events`

数据在各层之间如何流动，详见：
- `nowthink.md`
- `math.md`

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
- `http://127.0.0.1:8000/mcp/bank`

### 2. 启动 Flutter

```powershell
cd client_flutter
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## 已实现 API

- `GET /api/v1/dashboard`
- `GET /api/v1/transactions`
- `POST /api/v1/transfers/classify-risk`
- `POST /api/v1/transfers/precheck`
- `POST /api/v1/transfers/secondary-check`
- `POST /api/v1/transfers/confirm`
- `POST /api/v1/transfers/cancel`
- `POST /api/v1/agent/chat`

## MCP 工具

- 账户摘要
- 交易列表
- 风险分类
- 预检
- 外部情报筛查
- 转账确认
- Trace 查询：
  - `get_transfer_trace`
  - `list_transfer_traces`

## 配置说明

参考根目录 `.env.example`：

- `APP_ENV`
- `SQLITE_PATH`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_BENCHMARK_TIMEOUT_SECONDS`
- `MCP_BANK_ENABLED`

说明：
- 模型密钥仅保留在后端
- 在证明前，不允许把 `precheck` 切成全量 Agent 热路径

## 测试与基准命令

### 后端回归

```powershell
server\.venv\Scripts\python -m pytest server\tests -q
```

### 后端基准

```powershell
server\.venv\Scripts\python server\tests\benchmark_v3_baseline.py
server\.venv\Scripts\python server\tests\benchmark_v3_llm_path.py
server\.venv\Scripts\python server\tests\benchmark_v3_precheck_shadow.py
```

### 前端

```powershell
cd client_flutter
flutter analyze --no-version-check
flutter test --no-version-check test/widget_test.dart
```

## 当前验证结果（2026-04-08）

- 后端回归：`55 passed`
- baseline：
  - `precheck cold avg/p95 = 39.63ms`
  - `precheck warm avg = 31.43ms`
  - `precheck warm p95 = 42.34ms`
  - `secondary cold avg/p95 = 178.37ms`
  - `secondary warm avg = 61.56ms`
  - `secondary warm p95 = 111.77ms`
- LLM benchmark：
  - isolated LLM path：`status=ok`，`avg 5403.69ms / p95 5905.08ms`
  - precheck all-Agent shadow：`status=ok`，`avg 2282.41ms / p95 2530.10ms / drift 0.0`
- 前端自动化：
  - `flutter test test/widget_test.dart`：14/14 通过
  - `flutter analyze`：No issues found

## 当前性能目标

- `precheck hot path <= 750ms`
- `deterministic risk decision subpath <= 300ms`
- `secondary-check avg <= 3s`
- `LLM path P95 <= 30s`

这些是公开基线的 3 倍 demo 口径，详情见 `math.md`。
