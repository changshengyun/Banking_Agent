# Backend Development Skill (Sentinel-Mobile)

## 适用范围
FastAPI 风控后端开发，包括路由、服务层、仓储层、测试与数据库演进。

## 目标
- 保持分层边界清晰：Route -> Service -> Repository。
- 决策逻辑集中在服务层，数据读写集中在仓储层。
- 接口与测试同步演进，保证回归稳定。

## 输入
- 业务规则：`pass/interrogate/block`。
- 风险分解：`flag_s`、`g_behavior`、`g_dynamic`、`final_risk`。
- 数据表：`risk_events`、`pending_transfers`、`risk_profiles`。

## 输出
- 可复用服务函数，避免路由层堆业务逻辑。
- 可追溯风控记录（请求上下文 + 决策结果 + 原因）。
- 可执行测试用例覆盖关键风控场景。

## 开发步骤
1. 路由层最小化
- 路由层只做 schema 接收与响应返回。
- 把判定逻辑放到 `BankHostService` / `RiskEngine`。

2. 服务层聚焦决策
- `precheck_transfer` 负责聚合上下文并调用风险引擎。
- `confirm_transfer` 严格校验 token 与 block 禁止确认。

3. 仓储层聚焦持久化
- 每个读写动作单一职责，字段命名与 schema 对齐。
- 风险数据（分值/原因）必须写入事件表与待确认表。

4. 数据库演进
- 新增字段需兼容历史库（迁移或补列）。
- 初始化脚本和种子数据保持幂等。

5. 测试策略
- API 测试覆盖 happy path + 风控拒绝路径。
- 场景测试覆盖低/中/高风险组合与一票否决。

## 检查清单
- [ ] 路由没有业务分支判断。
- [ ] `block` token 在 confirm 必定失败。
- [ ] 风险分值范围稳定在 `[0, 1]`。
- [ ] 原因列表可解释且可落库。
- [ ] 测试包含回归场景与边界场景。

## 反模式
- 在 repository 内计算决策分值。
- 直接在路由中写 SQL 或拼业务文本。
- 改了 schema 不补测试与 DB 兼容逻辑。

## 参考
- FastAPI Bigger Applications：https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI Dependencies：https://fastapi.tiangolo.com/tutorial/dependencies/
- FastAPI Testing：https://fastapi.tiangolo.com/tutorial/testing/
