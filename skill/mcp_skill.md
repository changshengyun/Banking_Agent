# MCP Development Skill (Sentinel-Mobile)

## 适用范围
Model Context Protocol 服务设计与接入，重点是银行风险工具的可组合性与容错。

## 目标
- 提供稳定、可审计、可降级的 MCP 工具层。
- 工具输入输出结构一致，便于 Agent 编排。
- 外部扩展能力故障不影响核心银行链路。

## 输入
- 业务工具需求：画像查询、风险分类、风险预检、交易确认。
- 后端服务函数：`get_dashboard`、`classify_transfer_risk`、`precheck_transfer`、`confirm_transfer`。
- 挂载策略：`/mcp/bank` 为核心。

## 输出
- 清晰的 MCP 工具目录和参数说明。
- 工具返回统一包含关键风险分解字段。
- 明确的降级行为与健康状态。

## 开发步骤
1. 工具定义
- 每个 MCP tool 单一职责，避免大而全工具。
- 输入参数显式化，避免隐式全局变量。

2. 输出标准化
- 风险相关工具固定返回 `risk_breakdown` 或 `risk_classification`。
- 对象字段保持与 API schema 对齐，减少二次映射。

3. 失败降级
- 非核心扩展能力失败时不影响 bank 工具。
- 无静态画像时返回 fallback，并标记 `source`。

4. 可观测性
- 记录工具调用次数、耗时、失败类型。
- 对高风险工具调用保留审计轨迹。

## 检查清单
- [ ] 核心工具可单独运行。
- [ ] 任一扩展能力故障不影响主流程。
- [ ] tool 返回结构有版本兼容策略。
- [ ] 风险工具输出可直接用于前端/Agent。

## 反模式
- 把业务核心逻辑复制到 MCP 层。
- 返回结构随意变更，导致调用方频繁改造。
- 工具失败直接中断主链路。

## 参考
- MCP 规范首页：https://modelcontextprotocol.io/introduction
- MCP Concepts：https://modelcontextprotocol.io/docs/concepts
- MCP Specification：https://spec.modelcontextprotocol.io/
