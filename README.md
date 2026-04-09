# Banking AI Demo Monorepo

基于 `Flutter + FastAPI + MCP + SQLite + OpenAI-compatible LLM` 的手机银行风控演示项目。  
当前活动阶段为 `V5 / Phase-1（启动准备中）`。`V4` 已于 2026-04-09 完成收口，完成范围为：
- `Track-A`：感知层能力建设
- `Track-B`：初版风险报告 Agent

## 当前状态（2026-04-09）

- `V4` 已完成“感知层 + 初版风险报告 Agent”双主线交付。
- 原 `V5` 的“初版风险报告 Agent”已前置并入 `V4`。
- 原 `V3` 性能优化线已冻结，当前仅保留性能观测，不作为版本完成阻塞项。
- 后端已完成风险报告生成、持久化、查询与 trace 审计接入。
- Flutter 已补齐二次校验后的风险报告查看入口。
- 自动化验收已通过：
  - `server\.venv\Scripts\python -m pytest server\tests -q` -> `58 passed`
  - `flutter analyze --no-version-check` -> `No issues found!`
  - `flutter test --no-version-check test\widget_test.dart` -> `All tests passed!`
- 之前的 Flutter 假性阻塞已解决，根因是 Flutter SDK Git 信任异常和命令执行目录错误。

## 版本治理规则

- 单一事实源：
  - `plan.md`：唯一活动执行计划与当前阶段
  - `MVP.md`：版本台账与里程碑状态
  - `README.md`：对外入口与验证结论摘要
- 每次开发后至少同步：`plan.md + MVP.md + README.md`
- 涉及架构或变量流变化时，再同步：`nowthink.md + math.md`
- 大版本完成（V1/V2/V3/V4/V5）必须同时满足：
  - 对应版本验收项通过
  - `pytest + flutter analyze + flutter test` 通过
  - 文档同步完成且无冲突
- 满足后执行：`git commit + git push`（默认当前工作分支）

## 当前能力

- 三态预检决策：`pass / interrogate / block`
- 单轮二次质询：`pass_secondary / interrogate / block_secondary`
- 显式取消交易：`POST /api/v1/transfers/cancel`
- explain pack：结构化解释面板
- 三类 Agent：领域初分、领域细分、语义分析
- 感知层快照：`perception_snapshot` 已进入关键 trace
- 风险报告：`secondary-check` 后生成并可按 `confirmation_token` 查询
- 审计链路：`trace_events` + MCP 查询

## 文档导航

- `README.md`
  - 项目总入口、启动方法、验证命令
- `MVP.md`
  - 版本台账、完整度评估、路线图
- `plan.md`
  - 当前唯一执行计划
- `nowthink.md`
  - 架构、数据流、代码映射、最终指标
- `math.md`
  - 公式、变量流、风险报告后置原则、时延目标推导
- `promode/codex_execution_rules.md`
  - Codex 固定执行规则正文
- `promode/development_requirements_summary.md`
  - 历史开发要求汇总入口

## 风控主链路

1. 前端发起 `precheck`
2. 后端聚合 `ClientContext`、知识库分类、外部情报
3. `RiskEngine` 计算 `flag_s / g_behavior / g_dynamic / final_risk`
4. 若为 `interrogate`，进入 `secondary-check`
5. `AgentService` 做二次质询语义分析
6. `RiskReportService` 在 `secondary-check` 之后生成结构化风险报告
7. 最终进入 `confirm / cancel / block`
8. 关键节点写入 `trace_events`

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
- `GET /api/v1/transfers/{confirmation_token}/risk-report`
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
- 风险报告 Agent 只负责生成说明，不负责业务裁决

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
flutter test --no-version-check test\widget_test.dart
```

## 当前验证结果（2026-04-09）

- 后端回归：`58 passed`
- Flutter analyze：`No issues found!`
- Flutter widget test：`All tests passed!`
- 风险报告链路：
  - 404 场景已覆盖
  - `secondary-check` 后可生成并查询报告
  - trace 已包含 `risk_report_generated`
- 性能：
  - 保留既有基线观测
  - 当前版本不将性能作为完成阻塞项

## 当前性能目标

- `precheck hot path <= 750ms`
- `deterministic risk decision subpath <= 300ms`
- `secondary-check avg <= 3s`
- `LLM path P95 <= 30s`

这些仍作为观测目标保留，但版本完成判定以功能、自动化验收和文档一致性为主。
