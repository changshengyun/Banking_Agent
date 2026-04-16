# Frontend Development Skill (Sentinel-Mobile)

## 适用范围
Flutter 手机银行客户端开发，重点覆盖风控交互链路与可观测性。

## 目标
- 保证“风控预检 -> 三态决策 -> 交易确认”体验完整。
- 让前端状态流清晰、可测试、可追踪。
- 行为特征采集可复用、低侵入、可扩展。

## 输入
- API 合约：`/api/v1/transfers/precheck`、`/api/v1/transfers/confirm`。
- 页面需求：`PASS/INTERROGATE/BLOCK` 三态 UI。
- 风控埋点字段：`input_pause_count`、`input_duration_ms`、`extra_signals`。

## 输出
- 页面状态机：`idle -> prechecking -> blocked/interrogate/pass -> confirming`。
- 统一 Context 构造器，保证每次调用接口都带完整上下文。
- 可复现的 UI 测试脚本（至少覆盖三态流程）。

## 开发步骤
1. 先定义页面状态和边界
- 把所有按钮可用性与状态绑定，避免重复提交。
- 明确 `block` 为终态，禁止进入确认接口。

2. 统一请求模型
- 统一使用 `ClientContextData` 序列化上下文。
- 只在一处维护字段映射，避免字段名漂移。

3. 行为信号采集
- 采集输入停顿次数与输入时长。
- 扩展信号放在 `extra_signals`，避免频繁改主模型。

4. 三态交互
- `pass`：直接确认。
- `interrogate`：先弹窗确认，再决定是否确认。
- `block`：明确拦截说明，禁止确认动作。

5. 失败恢复
- 网络异常、业务异常、风控拒绝要区分提示文案。
- 任意失败后应可重试并回到稳定状态。

## 检查清单
- [ ] 三态都能在 UI 触发并正确流转。
- [ ] `confirmation_token` 生命周期清晰，仅用于一次确认。
- [ ] 上下文字段齐全，缺省值可控。
- [ ] 交互中断（取消、关闭弹窗）不会造成状态错乱。
- [ ] 关键流程有 widget/integration test 覆盖。

## 反模式
- 在多个文件重复拼接 context JSON。
- 在 `block` 状态仍调用 confirm。
- 把业务状态和显示状态耦合成一个布尔值。

## 参考
- Flutter 架构指南：https://docs.flutter.dev/app-architecture
- Flutter 架构分层（Guide）：https://docs.flutter.dev/app-architecture/guide
- Flutter 状态管理：https://docs.flutter.dev/data-and-backend/state-mgmt
