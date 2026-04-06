# Sentinel-Mobile Codex 执行流程

## 1. 文件定位

- `MVP.md`：唯一的阶段路线图、DoD 和阶段完成汇总。
- `work_now.md`：Codex 当前执行流程、技术总监监督门禁、多 Agent 协作编排。
- `README.md`：对外同步当前真实能力、运行方式和测试方式。
- `skill/project-manager/SKILL.md`：项目经理 SOP skill。
- `skill/architect/SKILL.md`：技术总监/架构师 skill。
- `skill/engineer/SKILL.md`：工程师 skill。
- `work.md`：已删除，不再维护。

## 2. 角色定义

### Boss

- 负责业务目标、优先级和验收方向。

### 技术总监 Agent

- 只读优先，默认不直接改业务代码。
- 职责：
  1. 对照 `MVP.md` 判断当前项目所处阶段。
  2. 审核是否严格按 MVP 顺序开发。
  3. 生成多 Agent 分工与门禁清单。
  4. 在每轮集成前做 DoD 审查。
  5. 在每个 MVP 结束时确认是否允许提交 Git。

### 主执行 Codex

- 负责主线程编排、集成、冲突处理、最终交付。
- 负责把技术总监 Agent 的结论真正落到代码、测试、README 和 Git 同步动作中。

### 下游开发 Agent

- 只负责被分配的明确子任务，遵守文件所有权边界，不互相覆盖改动。

## 3.1 SOP Skill 映射

### Project Manager Skill

- 核心任务：把架构图、MVP 阶段目标和依赖关系拆成可执行 Task。
- 关注点：开发顺序、所有权边界、并行不冲突、阶段收口。

### Architect Skill

- 核心任务：把一句话需求变成系统设计。
- 关注点：API 契约、数据结构、组件拓扑、兼容边界、测试影响。

### Engineer Skill

- 核心任务：根据已确认契约实现单一模块并补测试。
- 关注点：单模块交付、最小 patch、同边界验证、不越权改共享合同。

## 3. 固定铁律

- 必须按 `V1 -> V2 -> V3 -> V4` 顺序推进，不允许跳级。
- 每次有实际开发改动，都要同步更新根目录 `README.md`。
- 每个 MVP 阶段完成后，必须执行：
  1. 技术总监 Agent 审查 DoD。
  2. 运行相关测试。
  3. 更新 `README.md`。
  4. 回填 `MVP.md` 当前阶段完成情况。
  5. `git add -> git commit -> git push`。
- 如果技术总监 Agent 判断当前版本未满足 DoD，不允许进入下一 MVP。

## 4. 当前阶段结论

- 当前结论：`MVP V2 已完成并进入 Git 收口 → MVP V3 待放行`。
- 当前开发主线：完成 V2 文档、测试与 Git 收口；V3 仅允许做范围澄清和技术预案，不启动代码开发。
- 当前禁止事项：
  - 不要提前展开 V4 运行时 Swarm 架构。
  - 不要在 V2 未闭环前引入大规模新基础设施。
  - 不要跳过 README 和 Git 同步。
  - V2-patch-2 依赖 V2-patch-1 完成后才能启动；V2-patch-3 依赖 V2-patch-2 完成后才能启动。

## 5. 当前版本的多 Agent 协作流程

### 技术总监 Agent 的监督门禁

1. 先对比 `MVP.md` 和当前代码，确认当前活跃阶段。
2. 输出本轮允许开发的任务范围，只能来自当前 MVP。
3. 为下游 Agent 划分不重叠的文件责任范围。
4. 在主执行 Codex 集成前，检查：
   - 是否超出当前 MVP 范围。
   - 是否更新了 README。
   - 是否补齐了测试与文档。
   - 是否满足当前 MVP 的 DoD。
5. 通过后才允许进入 Git 提交流程。

### 四道固定门禁

#### 门禁 1：合同门禁

- schema、接口、字段命名、测试样例必须一致。
- 若后端返回结构变化而前端和测试未同步，不允许合并。

#### 门禁 2：质量门禁

- 后端测试、前端测试、最小手工回归至少各过一轮。
- 任一关键回归失败，不允许进入下一 MVP。

#### 门禁 3：文档门禁

- 每次 MVP 完成必须同步更新 `README.md`、`MVP.md` 和相关测试/演示文档。
- 文档若仍描述旧能力、旧接口或旧阶段判断，视为未完成。

#### 门禁 4：发布门禁

- 每次 MVP 完成必须执行一次独立 Git 提交。
- 未完成独立提交与推送，不允许宣告进入下一阶段开发。

### 当前版本建议的 Agent 分工

#### Agent A：感知/MCP 后端 Agent

- 负责范围：`server/app/services/`、`server/app/api/`、`server/app/schemas/`、`mcp_servers/`。
- 当前任务：
  1. 补齐 V2 所需的解释包/XAI 数据结构。
  2. 统一感知输入边界，梳理 `ClientContext`、KYC、地理位置、设备与行为信号的使用方式。
  3. 为外部情报工具提供稳定接口层，并同步到 MCP。

#### Agent B：前端 XAI/交互 Agent

- 负责范围：`client_flutter/lib/`。
- 当前任务：
  1. 在风险弹窗或独立面板中展示解释包。
  2. 让用户能看懂“为什么被怀疑、哪一层信号触发、下一步该怎么做”。
  3. 保持现有账单弹窗与二次质询流程不回退。

#### Agent C：测试与文档 Agent

- 负责范围：`server/tests/`、`client_flutter/test/`、`docs/`、`README.md`。
- 当前任务：
  1. 为 V2 的解释包/XAI 展示补测试。
  2. 统一演示脚本、测试样例与 README 描述。
  3. 确保每轮改动都能被回归验证。

### 主执行 Codex 的集成顺序

1. 先让技术总监 Agent确认本轮目标只属于当前 MVP。
2. 并行推进 Agent A 与 Agent B。
3. 在后端接口稳定后，交给 Agent C 补测试与 README。
4. 主执行 Codex 负责最终集成、冲突处理和验收。
5. 再由技术总监 Agent 做最终放行审查。

## 6. 按 MVP 顺序的 Codex 开发流程

### 第一步：关闭 V1

- 仅允许处理 V1 收尾问题：
  - 修正文档与测试口径不一致。
  - 清理旧 mock、旧原型、旧描述残留。
  - 保证 README 与当前实现一致。
- 退出条件：`MVP V1` 小节的 DoD 全部为已完成。

### 第二步：推进 V2（当前主线）

- 开发顺序固定为：
  1. `V2.1` 感知上下文标准化。
  2. `V2.2` 最小 XAI 看板。
  3. `V2.3` 外部情报工具适配层。
- 当前状态：`V2.1 + V2.2 + V2.3` 已完成实现与回归。
- 当前轮次的最小交付：
  - 后端返回结构化解释包。
  - 前端展示可折叠或直出的 XAI 风险解释面板。
  - README、测试、演示脚本同步更新。
  - 外部情报结果可进入预检、二次质询与 MCP 工具链路。

### 第二步补丁：V2-patch（已完成）

> 背景：V2 主体功能已完成，但代码审查发现三个阻塞性问题需在进入 V3 前修复：
> 1. 风险知识库关键词覆盖不足，字面匹配导致场景误判。
> 2. 二次质询追问内容与风险类型无关，Agent 缺乏场景锚点。
> 3. Agent 无法识别用户回复中的语义错误信息（如"我是警察让我转的"被当作正常说明）。

#### V2-patch-1：扩充风险知识库（无依赖，优先执行）

**问题根源**：`risk_knowledge_base.py` 中 `DEFAULT_RISK_SCENARIOS` 关键词覆盖面窄，高危短语与普通关键词权重相同（均+3分），`semantic_summary` 为空时直接返回低风险。

**交付物**：

- 文件：`server/app/services/risk_knowledge_base.py`
  - 为每个场景补充关键词，覆盖口语化表达（如"帮我付一下"→熟人借款、"说我涉案"→冒充公检法）。
  - 高危短语命中分值从 +3 提升至 +6，与普通关键词区分。
  - `semantic_summary` 为空时，改为基于 `amount + city + is_known_payee` 做兜底分类，不直接返回低风险。
  - 新增风险场景：
    - `investment_fraud`（投资理财诈骗）：关键词含"内部消息"、"稳赚"、"跟单"、"私募"。
    - `romance_scam`（情感诈骗）：关键词含"网恋"、"见面前转账"、"礼物清关"。
    - `part_time_fraud`（刷单兼职诈骗）：关键词含"刷单"、"垫付"、"佣金"、"任务单"。
  - 完善用户画像字段：在 `RiskScenario` 中增加 `target_user_profile` 字段，标注该场景的典型受害者特征（如"老年用户"、"在校学生"），供后续用户画像匹配使用。

- 文件：`server/app/schemas/risk.py`
  - `RiskClassificationPayload` 增加 `high_risk_phrase_hits: list[str]` 字段，区分普通关键词命中和高危短语命中。

- 文件：`server/tests/test_risk_scenarios.py`
  - 补充新场景的分类测试用例，覆盖口语化输入。

**完成标准**：
- [x] 新增3个风险场景，关键词总量显著扩充。
- [x] 高危短语命中可独立触发 `risk_level=high`（即使普通关键词未命中）。
- [x] `semantic_summary` 为空时，金额≥5000 且新增收款人的场景不再返回 `risk_level=low`。
- [x] 新场景测试用例全部通过。

---

#### V2-patch-2：差异化追问注入（依赖 V2-patch-1）

**问题根源**：`bank_host.py` 中 `secondary_question` 写死为通用问题，`agent_service` 收到的 `follow_up_questions` 虽然按场景生成，但未被注入到 Agent 的系统提示词中作为强制追问框架。

**交付物**：

- 文件：`server/app/services/bank_host.py`
  - `secondary_check_transfer()` 中，将 `secondary_question` 改为从 `risk_classification.follow_up_questions` 动态取第一条，而非写死通用问题。
  - 将 `risk_classification.follow_up_questions` 和 `risk_classification.matched_scenarios` 一并传入 `evaluate_secondary_intercept()`。

- 文件：`server/app/services/agent_service.py`（或对应 Agent 提示词构建函数）
  - 在 Agent 系统提示词中，按 `risk_category` 注入对应的追问框架：
    - `冒充公检法`：强制追问"是否通过官方电话核实案号"、"是否被要求转账核验"。
    - `安全账户诈骗`：强制追问"对方是否明确说转到安全账户"、"是否要求提供验证码"。
    - `熟人借款风险`：强制追问"是否视频核验身份"、"是否有共同联系人可确认"。
    - `客服退款诈骗`：强制追问"是否通过官方App核实"、"是否被要求下载软件"。
    - `验证码/屏幕共享诈骗`：强制追问"是否有人索取验证码"、"是否被要求开启屏幕共享"。
    - `投资理财诈骗`（新增）：强制追问"对方是否承诺稳定收益"、"是否在非官方平台操作"。
    - `情感诈骗`（新增）：强制追问"是否线下见过面"、"是否被要求转账才能见面"。
    - `刷单兼职诈骗`（新增）：强制追问"是否需要先垫付资金"、"是否通过官方平台接单"。

**完成标准**：
- [x] 二次质询的追问问题与风险类型一一对应，不再使用通用问题。
- [x] Agent 提示词中包含当前风险场景的强制核验点。
- [x] 测试用例覆盖：冒充公检法场景下，Agent 必须追问"官方电话核实"相关内容。

---

#### V2-patch-3：Agent 语义识别增强（依赖 V2-patch-2）

**问题根源**：Agent 当前仅靠 LLM 通用判断用户回复，缺乏对"高风险回复模式"的识别规则，导致"警察让我转的"、"客服说要验证资金"等高危回复可能被当作正常说明放行。

**交付物**：

- 文件：`server/app/services/agent_service.py`
  - 在 `evaluate_secondary_intercept()` 的提示词中增加"高风险回复模式识别"规则层：
    - 若用户回复中出现以下模式，Agent 必须输出 `block_secondary`，不得放行：
      - 提及"公安/警察/检察/法院要求转账"。
      - 提及"安全账户/资金清查/冻结前转账"。
      - 提及"客服要求验证资金/刷流水"。
      - 提及"对方要求提供验证码/屏幕共享"。
      - 提及"稳赚/内部消息/跟单收益"。
    - 若用户回复与 `risk_category` 完全无关（如被问"是否视频核验"，回复"我就是想转账"），Agent 应输出 `interrogate` 并追加追问，不得直接放行。
  - 增加 `semantic_red_flags: list[str]` 字段到 Agent 返回结构，记录命中的高风险语义模式，供 `explain_pack` 展示。

- 文件：`server/app/schemas/transfer.py`
  - `TransferSecondaryCheckResponse` 增加 `semantic_red_flags: list[str]` 字段（可为空列表）。

- 文件：`server/tests/test_api.py`
  - 补充测试用例：
    - 用户回复"警察让我转的" → 必须 `block_secondary`。
    - 用户回复"客服说验证资金后退款" → 必须 `block_secondary`。
    - 用户回复与问题无关 → 必须 `interrogate` 或 `block_secondary`，不得 `pass_secondary`。

**完成标准**：
- [x] 高风险回复模式命中时，Agent 强制输出 `block_secondary`。
- [x] `semantic_red_flags` 字段在命中时非空，并已进入二次质询接口响应。
- [x] 上述三条测试用例全部通过。

### 第三步：V3 只在 V2 通过后启动

- 先行为感知，再隐私护栏，再合规建议。
- 未通过 V2 DoD 前，不允许启动 V3 主开发。

### 第四步：V4 最后启动

- 只有在 V1-V3 形成稳定输入、解释、隐私和合规基础后，才进入治理闭环与运行时多 Agent 架构。

## 7. 每轮开发完成后的固定收口动作

1. 更新根目录 `README.md`。
2. 回填 `MVP.md` 当前阶段状态。
3. 运行受影响测试。
4. 由技术总监 Agent 做 DoD 审查。
5. Git 同步：
   - `git status`
   - `git add`
   - `git commit`
   - `git push`

## 8. 当前版本的下一开发指令

- 当前执行顺序：
  1. **V2 收口**：更新 README、回填 MVP.md、整理 Showme_func、运行全量测试、执行 Git 提交。
  2. **V3 放行审查**：仅在 V2 Git 同步完成后，由技术总监 Agent 放行进入 V3。
  3. **V3 启动**：先做行为信号建模边界，再做隐私护栏与合规建议。

- 当前禁止事项：
  - 不允许在 V2 Git 收口完成前宣告进入 V3 主开发。
  - 不允许跳过 README / MVP / Showme_func 的同步更新。
  - 不允许跳过后端与前端回归测试。

- V3 预备动作（当前允许整理，不允许提前大规模动代码）：
  - 整理 S3 行为脉冲模型的信号采集清单。
  - 评估向量检索替代字面关键词匹配的引入成本（作为 V3 技术选型输入）。

## 9. V2 收口验证结果

- `server/tests/test_api.py`：14 通过
- `server/tests/test_risk_scenarios.py`：13 通过
- `server/tests/test_patch2_secondary_followup.py`：2 通过
- `flutter analyze --no-version-check`：通过
- `flutter test --no-version-check`：6 通过
