# Showme Func

本文件汇总截至 `V2-patch-3` 的关键函数/结构职责说明，并标注其在 HIRD 四层架构中的归属。

HIRD 分层约定：
- `H` 感知层：采集、读取、清洗、整理原始上下文与知识数据
- `I` 识别层：完成场景分类、语义命中、风险归因
- `R` 推理层：完成解释、复核、综合判断与提示词编排
- `D` 治理层：执行放行、拦截、审计留痕与控制面决策

## V2-patch-1

### [server/app/services/risk_knowledge_base.py](e:/Projects/Banking_AI_Project/server/app/services/risk_knowledge_base.py)

### `RiskScenario.embedding_text`
- HIRD 层：`H`
- 职责：把场景标题、描述、关键词、高危短语、可疑行为、目标用户画像拼成统一索引文本。
- 本轮作用：让新增诈骗场景具备统一的检索与落库表示。

### `ensure_seeded()`
- HIRD 层：`I`
- 职责：把默认风险场景写入 `risk_scene_knowledge`，并在冲突时更新已有记录。
- 本轮作用：新增投资理财诈骗、情感诈骗、刷单兼职诈骗等场景种子数据。

### `classify_text()`
- HIRD 层：`I`
- 职责：根据语义文本和上下文信号完成风险场景分类，返回标准化 `RiskClassificationPayload`。
- 本轮作用：输出 `high_risk_phrase_hits`，并在明确诈骗语义命中时避免被泛化场景覆盖。

### `_build_contextual_fallback()`
- HIRD 层：`I`
- 职责：当语义为空或无命中时，基于城市、金额、收款人关系构建兜底风险分类。
- 本轮作用：保证空摘要场景仍能落入可解释的异常转账分类。

### `_build_normal_result()`
- HIRD 层：`I`
- 职责：构造正常转账的低风险标准返回结构。
- 本轮作用：统一 `high_risk_phrase_hits=[]` 的接口契约。

### `_score_scenario()`
- HIRD 层：`I`
- 职责：计算单个场景的关键词分、短语分和上下文分，形成可排序分类结果。
- 本轮作用：为显式诈骗语义优先级提供排序基础。

### `_load_scenarios()`
- HIRD 层：`H`
- 职责：从数据库读取最新风险知识场景并恢复成 `RiskScenario` 对象。
- 本轮作用：支持扩展字段稳定读取。

### `_collect_matches()`
- HIRD 层：`H`
- 职责：从输入文本中提取命中的关键词或高危短语。
- 本轮作用：统一清洗规则，提升匹配稳定性。

### `_risk_level_rank()`
- HIRD 层：`I`
- 职责：把风险等级转换为可排序权重。
- 本轮作用：用于多场景竞争时的稳定排序。

### `_scenario_by_id()`
- HIRD 层：`H`
- 职责：按场景 ID 获取默认知识库中的目标场景。
- 本轮作用：为空语义兜底逻辑提供标准场景对象。

### `_unique()`
- HIRD 层：`H`
- 职责：对关键词、短语、问题列表做去重和清洗。
- 本轮作用：防止重复命中污染分析结果。

### `get_risk_knowledge_base_service()`
- HIRD 层：`H`
- 职责：提供风险知识库服务的单例入口。
- 本轮作用：保证分类服务实例一致。

## V2-patch-2

### [server/app/services/bank_host.py](e:/Projects/Banking_AI_Project/server/app/services/bank_host.py)

### `secondary_check_transfer()`
- HIRD 层：`D`
- 职责：执行二次质询主链路，读取待确认转账、选择主问题、调用 Agent 完成二次放行/拦截并落库。
- 本轮作用：把 `follow_up_questions[0]` 作为 `secondary_question` 落库，并把场景追问信息传给 Agent。

### `_select_secondary_question()`
- HIRD 层：`R`
- 职责：从风险分类生成的追问列表中选出本轮二次质询主问题。
- 本轮作用：将二次质询从固定问句改为场景化问句。

### `_build_classification_text()`
- HIRD 层：`I`
- 职责：提取供知识库分类使用的核心语义文本。
- 本轮作用：减少页面上下文噪声对诈骗场景识别的干扰。

### [server/app/services/agent_service.py](e:/Projects/Banking_AI_Project/server/app/services/agent_service.py)

### `evaluate_secondary_intercept()`
- HIRD 层：`R`
- 职责：把风险分类、命中场景、关键词、追问点和用户解释组装成二次拦截判断输入，并解析模型输出。
- 本轮作用：把场景化追问骨架真正注入二次拦截 Agent。

### `_build_secondary_system_prompt()`
- HIRD 层：`R`
- 职责：定义二次拦截模型的全局规则、输出格式和判断边界。
- 本轮作用：明确模型必须围绕强制核验点判断用户解释是否充分。

### `_build_secondary_user_prompt()`
- HIRD 层：`R`
- 职责：把预检摘要、风险等级、命中场景、建议追问点、强制核验点和用户解释拼装为提示词。
- 本轮作用：让模型看到完整的场景化复核上下文。

### `_secondary_verification_points()`
- HIRD 层：`R`
- 职责：按风险类型生成当前轮必须覆盖的核验点，并与知识库追问点合并去重。
- 本轮作用：为不同诈骗场景注入差异化复核框架。

### `_unique_strings()`
- HIRD 层：`H`
- 职责：清洗和去重二次质询提示词里的核验点列表。
- 本轮作用：保持提示词稳定、避免重复追问。

## V2-patch-3

### [server/app/services/agent_service.py](e:/Projects/Banking_AI_Project/server/app/services/agent_service.py)

### `evaluate_secondary_intercept()`
- HIRD 层：`R`
- 职责：执行二次拦截复核总控，先跑本地红旗规则与无关回复识别，再决定是否调用在线模型。
- 输入：`user_reply`、`semantic_summary`、`risk_category`、`risk_level`、`matched_keywords`、`matched_scenarios`、`follow_up_questions`
- 输出：`tuple[str, float, list[str], str, list[str]]`
- 本轮作用：
  - 新增 `semantic_red_flags` 返回值
  - 对硬红旗语义先本地阻断
  - 对无关回复至少返回 `interrogate`
  - 对模型输出做阻断一致性校验

### `_detect_semantic_red_flags()`
- HIRD 层：`I`
- 职责：识别用户回复是否命中高风险语义标签集合。
- 输入：`user_reply`
- 输出：`list[str]`
- 本轮作用：为“司法机关要求转账”“安全账户/资金清查”“客服要求验证资金”等场景提供确定性直拦能力。

### `_build_red_flag_block_result()`
- HIRD 层：`R`
- 职责：把命中的语义红旗集合转换成标准阻断结果。
- 输入：`semantic_red_flags`
- 输出：`tuple[str, float, list[str], str, list[str]]`
- 本轮作用：统一硬红旗命中后的风险分、原因文案和用户提示。

### `_is_irrelevant_reply()`
- HIRD 层：`I`
- 职责：判断用户回复是否没有覆盖当前风险核验点，或属于回避性回复。
- 输入：`user_reply`、`risk_category`、`verification_points`
- 输出：`bool`
- 本轮作用：阻止“我就是想转账”“别问了”这类内容直接通过二次复核。

### `_extract_relevant_tokens()`
- HIRD 层：`H`
- 职责：从文本中提取用于规则匹配的关键词 token。
- 输入：`text`
- 输出：`set[str]`
- 本轮作用：为“回复是否相关”判断提供轻量关键词支撑。

### `_normalize_text()`
- HIRD 层：`H`
- 职责：归一化文本，供规则匹配与 token 提取复用。
- 输入：`text`
- 输出：`str`
- 本轮作用：统一空格、大小写处理，降低规则误差。

### `_build_secondary_system_prompt()`
- HIRD 层：`R`
- 职责：定义二次拦截模型的系统规则。
- 本轮作用：允许模型输出 `pass_secondary / interrogate / block_secondary` 三态结果，并明确“无关回复不得直接放行”。

### `_build_secondary_user_prompt()`
- HIRD 层：`R`
- 职责：构建二次拦截模型用户提示词。
- 本轮作用：新增 `semantic_red_flags` JSON 契约，确保模型返回结构与后端一致。

### `_parse_secondary_json()`
- HIRD 层：`R`
- 职责：校验并解析二次拦截模型输出的结构化 JSON。
- 输入：`payload`
- 输出：`tuple[str, float, list[str], str, list[str]]`
- 本轮作用：解析并清洗 `semantic_red_flags`，为后端治理层提供结构化结果。

### [server/app/services/bank_host.py](e:/Projects/Banking_AI_Project/server/app/services/bank_host.py)

### `secondary_check_transfer()`
- HIRD 层：`D`
- 职责：执行二次质询、落库审计字段并返回前端响应。
- 本轮作用：
  - 接收 Agent 返回的五元组结果
  - 在响应中透传 `semantic_red_flags`
  - 放行路径统一返回空 `semantic_red_flags`

### [server/app/schemas/transfer.py](e:/Projects/Banking_AI_Project/server/app/schemas/transfer.py)

### `TransferSecondaryCheckResponse`
- HIRD 层：`D`
- 职责：定义二次质询接口的标准响应结构。
- 本轮作用：新增 `semantic_red_flags: list[str]` 字段，用于前端展示命中的语义风险标签。

## 当前版本验证结果

- `server\.venv\Scripts\python -m py_compile server/app/services/agent_service.py server/app/services/bank_host.py server/app/schemas/transfer.py server/tests/test_api.py`：通过
- `server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider`：14 通过
- `server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider`：13 通过

## V2-patch-3 已验证行为

- 命中“警察让我转账”等高风险语义时，二次质询直接 `block_secondary`
- 命中“客服让我验证资金后退款”“先刷流水”等话术时，返回非空 `semantic_red_flags`
- 对“我就是想转账，别问了”这类回避性回复，不会直接 `pass_secondary`
- 二次质询 API 响应契约已稳定包含 `semantic_red_flags`
