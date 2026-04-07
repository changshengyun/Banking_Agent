# Sentinel-Mobile Codex 执行流程

## 1. 文件定位

- `MVP.md`：唯一的阶段路线图、DoD 和阶段完成汇总。
- `work_now.md`：Codex 当前执行流程、技术总监监督门禁、多 Agent 协作编排。
- `README.md`：对外同步当前真实能力、运行方式和测试方式。
- `skill/project-manager/SKILL.md`：项目经理 SOP skill。
- `skill/architect/SKILL.md`：技术总监/架构师 skill。
- `skill/engineer/SKILL.md`：工程师 skill。

## 2. 角色定义

### Boss

- 负责业务目标、优先级和验收方向。

### 技术总监 Agent（Architect Skill）

- 只读优先，默认不直接改业务代码。
- 职责：
  1. 对照 `MVP.md` 判断当前项目所处阶段。
  2. 审核是否严格按 MVP 顺序开发。
  3. 生成多 Agent 分工与门禁清单。
  4. 在每轮集成前做 DoD 审查。
  5. 在每个 MVP 结束时确认是否允许提交 Git。

### 项目经理 Agent（Project Manager Skill）

- 职责：
  1. 把 MVP 目标拆成最小可交付任务切片。
  2. 建立依赖顺序：合同先行 → 后端/前端并行 → 测试/文档收尾。
  3. 划定文件所有权边界，防止 Agent 互相覆盖。
  4. 定义合并门禁清单。

### 主执行 Codex

- 负责主线程编排、集成、冲突处理、最终交付。
- 负责把技术总监 Agent 的结论真正落到代码、测试、README 和 Git 同步动作中。
- **每完成一个任务切片，立即执行 `/simplify` 对变更代码做质量审查。**

### 下游开发 Agent（Engineer Skill）

- 只负责被分配的明确子任务，遵守文件所有权边界，不互相覆盖改动。

## 3. SOP Skill 映射

### Project Manager Skill

- 核心任务：把架构图、MVP 阶段目标和依赖关系拆成可执行 Task。
- 关注点：开发顺序、所有权边界、并行不冲突、阶段收口。

### Architect Skill

- 核心任务：把一句话需求变成系统设计。
- 关注点：API 契约、数据结构、组件拓扑、兼容边界、测试影响。

### Engineer Skill

- 核心任务：根据已确认契约实现单一模块并补测试。
- 关注点：单模块交付、最小 patch、同边界验证、不越权改共享合同。

## 4. 固定铁律

- 必须按 `V1 -> V2 -> V3 -> V4` 顺序推进，不允许跳级。
- 每次有实际开发改动，都要同步更新根目录 `README.md`。
- **每完成一个任务切片，执行 `/simplify` 审查变更代码。**
- 每个 MVP 阶段完成后，必须执行：
  1. 技术总监 Agent 审查 DoD。
  2. 运行相关测试（后端 pytest + 前端 flutter test）。
  3. 更新 `README.md`。
  4. 回填 `MVP.md` 当前阶段完成情况。
  5. `git add -> git commit -> git push`。
- 如果技术总监 Agent 判断当前版本未满足 DoD，不允许进入下一 MVP。

## 5. 当前阶段结论

- **当前结论：`MVP V2 已完成 → MVP V3 正式放行开发`。**
- V2 收口验证已通过（见第 9 节）。
- V3 主开发线：语义感知升级 → 行为脉冲建模 → 隐私护栏。

## 6. V3 多 Agent 协作流程

### 技术总监 Agent 的监督门禁

1. 先对比 `MVP.md` 和当前代码，确认当前活跃阶段为 V3。
2. 输出本轮允许开发的任务范围，只能来自 V3 DoD。
3. 为下游 Agent 划分不重叠的文件责任范围。
4. 在主执行 Codex 集成前，检查：
   - 是否超出 V3 范围。
   - 是否更新了 README。
   - 是否补齐了测试与文档。
   - 是否满足 V3 DoD。
5. 通过后才允许进入 Git 提交流程。

### 四道固定门禁

#### 门禁 1：合同门禁

- schema、接口、字段命名、测试样例必须一致。
- 若后端返回结构变化而前端和测试未同步，不允许合并。

#### 门禁 2：质量门禁

- 后端测试、前端测试、最小手工回归至少各过一轮。
- **每个任务切片完成后执行 `/simplify`，质量审查通过后才能进入下一切片。**
- 任一关键回归失败，不允许进入下一 MVP。

#### 门禁 3：文档门禁

- 每次 MVP 完成必须同步更新 `README.md`、`MVP.md` 和相关测试/演示文档。
- 文档若仍描述旧能力、旧接口或旧阶段判断，视为未完成。

#### 门禁 4：发布门禁

- 每次 MVP 完成必须执行一次独立 Git 提交。
- 未完成独立提交与推送，不允许宣告进入下一阶段开发。

### V3 Agent 分工

#### Agent A：语义升级后端 Agent

- 负责范围：`server/app/services/risk_knowledge_base.py`、`server/app/services/agent_service.py`。
- V3 任务：
  1. 引入 `BAAI/bge-small-zh-v1.5`（95MB，CPU 友好）替代纯关键词匹配。
  2. 实现双阶段语义检索：向量召回（FAISS）→ 关键词精排。
  3. 保持现有 `RiskClassificationPayload` 合同不变，仅升级内部检索逻辑。

#### Agent B：行为脉冲建模 Agent

- 负责范围：`server/app/services/risk_engine.py`、`server/app/schemas/`。
- V3 任务：
  1. 建立 S3 行为脉冲模型：输入停顿分布、输入时长、粘贴次数、切换次数。
  2. 把行为信号从简单阈值升级为加权脉冲评分。
  3. 新增 `behavior_pulse_score` 字段到 `RiskAssessment`（向后兼容）。

#### Agent C：隐私护栏 Agent

- 负责范围：`server/app/api/routes/`、`server/app/schemas/`。
- V3 任务：
  1. 在 API 入口对 `semantic_summary` 做 PII 脱敏（姓名、手机号、身份证号替换为占位符）。
  2. 确保 LLM 调用链路不暴露明文敏感信息。
  3. 新增 `pii_masked: bool` 字段到请求日志（不进入响应体）。

#### Agent D：测试与文档 Agent

- 负责范围：`server/tests/`、`client_flutter/test/`、`docs/`、`README.md`。
- V3 任务：
  1. 为语义升级补回归测试（相同输入，语义匹配结果不低于关键词匹配）。
  2. 为行为脉冲评分补单元测试。
  3. 更新 README 和演示脚本。

### 主执行 Codex 的集成顺序

1. 技术总监 Agent 确认本轮目标只属于 V3。
2. **Agent A（语义升级）先行**，因为它影响分类合同的内部实现。
3. Agent B（行为脉冲）与 Agent A 并行，写集不重叠。
4. Agent C（隐私护栏）在 Agent A/B 稳定后启动，只改 API 入口层。
5. Agent D 在接口稳定后补测试与文档。
6. 主执行 Codex 负责最终集成、冲突处理和验收。
7. 技术总监 Agent 做最终放行审查。

## 7. V3 开发任务清单（按依赖顺序）

### 阶段 V3.1：语义检索升级（优先执行，无外部依赖）

**目标**：用向量语义相似度替代纯关键词字面匹配，解决"关键词匹配无法识别语义变体"的核心问题。

**技术选型**：
- 模型：`BAAI/bge-small-zh-v1.5`（95MB，CPU 推理，sentence-transformers 兼容）
- 向量库：`faiss-cpu`（纯 Python/C++，无需服务器）
- 推理加速：`fastembed` 或直接 `sentence-transformers`

**任务切片**：

| # | 任务 | 负责 Agent | 文件边界 |
|---|------|-----------|---------|
| V3.1-a | 安装依赖，封装 `EmbeddingService`（单例，懒加载模型） | Agent A | `server/app/services/embedding_service.py`（新建） |
| V3.1-b | 在 `RiskKnowledgeBaseService` 中新增向量索引构建逻辑 | Agent A | `server/app/services/risk_knowledge_base.py` |
| V3.1-c | 把 `classify_text` 改为双阶段：向量召回 Top-5 → 关键词精排 | Agent A | `server/app/services/risk_knowledge_base.py` |
| V3.1-d | 补回归测试：语义变体输入（如"说我涉案"）能正确分类 | Agent D | `server/tests/test_risk_scenarios.py` |

**完成标准**：
- [ ] 语义变体输入（不含关键词但语义相近）能正确命中风险场景。
- [ ] 现有 29 条测试全部通过（不回退）。
- [ ] 模型加载时间 < 5s，单次分类延迟 < 200ms（CPU）。

---

### 阶段 V3.2：行为脉冲建模（与 V3.1 并行）

**目标**：把行为信号从简单阈值判断升级为加权脉冲评分，提升行为风险的区分度。

**任务切片**：

| # | 任务 | 负责 Agent | 文件边界 |
|---|------|-----------|---------|
| V3.2-a | 定义 `BehaviorPulse` 数据类，封装脉冲评分逻辑 | Agent B | `server/app/services/risk_engine.py` |
| V3.2-b | 把 `_calculate_behavior_score` 升级为脉冲加权版本 | Agent B | `server/app/services/risk_engine.py` |
| V3.2-c | `RiskAssessment` 新增 `behavior_pulse_score` 字段（向后兼容） | Agent B | `server/app/services/risk_engine.py`、`server/app/schemas/` |
| V3.2-d | 补行为脉冲单元测试 | Agent D | `server/tests/test_risk_scenarios.py` |

**完成标准**：
- [ ] 高频停顿 + 粘贴 + 切换 App 的组合能触发更高行为风险分。
- [ ] 现有行为相关测试不回退。

---

### 阶段 V3.3：PII 隐私护栏（依赖 V3.1 完成后启动）

**目标**：确保进入 LLM 的文本不含明文 PII，满足最小化原则。

**任务切片**：

| # | 任务 | 负责 Agent | 文件边界 |
|---|------|-----------|---------|
| V3.3-a | 实现 `PiiMasker`：正则替换手机号、身份证号、姓名模式 | Agent C | `server/app/services/pii_masker.py`（新建） |
| V3.3-b | 在 `AgentService._live_chat_response` 和 `evaluate_secondary_intercept` 入口调用 `PiiMasker` | Agent C | `server/app/services/agent_service.py` |
| V3.3-c | 补 PII 脱敏单元测试 | Agent D | `server/tests/` |

**完成标准**：
- [ ] 含手机号/身份证号的 `semantic_summary` 进入 LLM 前已脱敏。
- [ ] 脱敏不影响风险分类结果（语义保留）。

---

### V3 收口（所有切片完成后）

1. 技术总监 Agent 对照 V3 DoD 做完成度审查。
2. 运行全量测试：`pytest server/tests/ -q` + `flutter test --no-version-check`。
3. 更新 `README.md`（新增语义升级、行为脉冲、PII 护栏说明）。
4. 回填 `MVP.md` V3 完成情况。
5. Git 同步：`git add -> git commit -> git push`。

## 8. 每轮开发完成后的固定收口动作

1. **执行 `/simplify` 审查本轮变更代码。**
2. 更新根目录 `README.md`。
3. 回填 `MVP.md` 当前阶段状态。
4. 运行受影响测试。
5. 由技术总监 Agent 做 DoD 审查。
6. Git 同步：
   - `git status`
   - `git add`
   - `git commit`
   - `git push`

## 9. V2 收口验证结果（已完成）

- `server/tests/test_api.py`：14 通过
- `server/tests/test_risk_scenarios.py`：13 通过
- `server/tests/test_patch2_secondary_followup.py`：2 通过
- `flutter analyze --no-version-check`：通过
- `flutter test --no-version-check`：6 通过

## 10. 技术选型备忘（V3 引入）

### 语义检索技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 中文嵌入模型 | `BAAI/bge-small-zh-v1.5` | 95MB，CPU 友好，中文语义质量优秀 |
| 向量检索库 | `faiss-cpu` | 纯 Python/C++，无需服务器，支持 IVF 索引 |
| 推理框架 | `sentence-transformers` | 与 BGE 模型直接兼容，API 简洁 |
| 备选加速 | `fastembed` | ONNX 后端，CPU 推理更快，依赖更轻 |

### 多 Agent 协作模式（本项目采用）

- **Orchestrator + Subagent 模式**：主执行 Codex 作为编排器，下游 Agent 各持独立文件边界。
- **Plan-file 模式**：每个 Agent 开始前写计划到 `skill/` 对应 SKILL.md，执行后回填结果。
- **Git worktree 隔离**：并行 Agent 使用独立 worktree，避免文件锁冲突。
- **人工检查点**：每个任务切片完成后，主执行 Codex 做集成审查，再由技术总监 Agent 放行。
