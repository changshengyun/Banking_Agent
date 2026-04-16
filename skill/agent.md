# Agent Development Skill (Sentinel-Mobile)

## 适用范围
银行风控 Agent 的对话编排、工具调用、策略约束与可解释输出。

## 目标
- Agent 输出稳定、可解释、可审计。
- 工具调用有边界，避免越权执行。
- 支持从“提示”向“质询/治理”平滑演进。

## 输入
- 用户消息与会话上下文。
- 可调用工具：银行摘要、交易列表、风控解释、MCP 风险预检。
- 控制策略：高风险拦截优先、低风险最小打扰。

## 输出
- 标准响应：`assistant_message` + `used_tools` + `suggested_actions`。
- 当触发风控解释时，输出原因与下一步建议。
- 当信息不足时，优先请求补充而不是臆断。

## 开发步骤
1. 系统提示词设计
- 明确角色：银行风控助手，不做法律/资金操作承诺。
- 明确边界：只基于工具与上下文回答，不杜撰账户事实。

2. 工具路由策略
- 优先银行工具，按用户意图调用最少工具。
- 工具调用失败要有降级回复，不中断会话。

3. 风控解释策略
- 对 `interrogate` 与 `block` 提供可理解原因。
- 输出要包含可执行建议（核验收款人、联系客服等）。

4. 质量守护
- 增加对“幻觉回答”的回归测试。
- 增加高风险话术样本，持续校正 prompt 与规则。

## 检查清单
- [ ] 每次回答都能追溯是否调用了工具。
- [ ] 关键回答不泄露敏感信息。
- [ ] 风控说明清晰，用户可执行下一步。
- [ ] mock 与 live 模式行为差异可控。

## 反模式
- 直接把模型原始输出透传给用户。
- 工具未调用却伪装成“已查询结果”。
- 高风险场景给出模糊建议，缺少明确动作。

## 参考
- OpenAI Function Calling：https://platform.openai.com/docs/guides/function-calling
- OpenAI Prompting Guide：https://platform.openai.com/docs/guides/prompt-engineering
- OpenAI Building Agents：https://platform.openai.com/docs/guides/agents
