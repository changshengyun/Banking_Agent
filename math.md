# math · 风险公式、变量流、场景算例与时延目标

> 本文档只负责四类内容：公式、变量、跨层数据流、性能目标推导。  
> 不承担版本排期职责。

## 1. 核心变量

| 变量 | 含义 | 当前来源 |
|---|---|---|
| `semantic_summary` | 用户语义摘要 | `ClientContext.semantic_summary` |
| `c_match` | 场景匹配置信度 | `RiskKnowledgeBase -> BankHost._derive_c_match()` |
| `flag_s` | 静态风险分 | `RiskEngine._calculate_static_score()` |
| `g_behavior` | 行为风险分 | `RiskEngine._calculate_behavior_pulse_score()` |
| `g_dynamic` | 动态/语义风险分 | `RiskEngine._calculate_dynamic_score()` |
| `secondary_risk` | 二次质询后的风险分 | `AgentService.evaluate_secondary_intercept()` |
| `w_base` | 基础权重 | `RiskEngine.W_BASE = 0.3` |
| `w_adj` | 动态调整后的权重 | 主公式中间量 |
| `f_final` | 最终综合风险分 | `RiskEngine.apply_dynamic_formula()` |

## 2. 当前主公式

### 2.1 动态权重
```text
w_adj = w_base + (1 - w_base) * c_match
```

### 2.2 最终风险分
```text
f_final = (1 - w_adj) * s_static + w_adj * s_dev
```

### 2.3 当前代码中的变量映射
- `s_static -> flag_s`
- `s_dev -> g_dynamic`
- `w_base -> 0.3`
- `c_match -> _derive_c_match(classification)`
- `f_final -> RiskAssessment.final_risk`

### 2.4 路由阈值
```text
f_final < 0.3      -> pass
0.3 <= f_final <= 0.8 -> interrogate
f_final > 0.8      -> block
```

### 2.5 硬拦截优先级
- 命中高危短语或外部情报硬拦截时：
```text
hard_block = True -> final_risk = 1.0 -> block
```

## 3. 数据在各层之间如何流动

### 3.1 感知层 -> 认知层
1. `ClientContext.semantic_summary`
2. `current_city`
3. `amount`
4. `recent_page`
5. `last_action`
6. `extra_signals`

这些字段进入：
- `RiskKnowledgeBase.classify_text()`
- `RiskEngine.assess()`

### 3.2 认知层 -> 治理层
`RiskKnowledgeBase.classify_text()` 产出：
- `risk_category`
- `risk_level`
- `matched_keywords`
- `matched_scenarios`
- `high_risk_phrase_hits`
- `block_hint`

`BankHostService._derive_c_match()` 再将其压缩成：
- `c_match`

### 3.3 治理层公式计算
`RiskEngine.assess()` 内部顺序：
1. 计算 `flag_s`
2. 计算 `g_behavior`
3. 计算 `g_dynamic`
4. 合并外部情报硬拦截
5. 根据 `c_match` 执行公式
6. 得到 `final_risk`
7. 路由到 `pass / interrogate / block`

### 3.4 二次质询数据流
`AgentService.evaluate_secondary_intercept()` 输入：
- `user_reply`
- `semantic_summary`
- `risk_category`
- `risk_level`
- `matched_keywords`
- `matched_scenarios`

输出：
- `decision`
- `risk`
- `semantic_red_flags`
- `domain_output`
- `deep_output`
- `semantic_output`

这些输出再流回治理层，形成：
- `secondary_decision`
- `secondary_risk`
- `trace_events.secondary_decided`

### 3.5 执行层与审计层
- `confirm -> trace_events.transfer_confirmed`
- `cancel -> trace_events.transfer_cancelled`
- 非法重复操作 -> `trace_events.transfer_rejected`
- `precheck_decided.payload` 最小性能字段：
  - `timing_total_ms`
  - `timing_external_intelligence_ms`
  - `timing_classification_ms`
  - `timing_engine_ms`
  - `timing_persistence_ms`
- `secondary_decided.payload` 最小性能字段：
  - `timing_total_ms`
  - `timing_classification_ms`
  - `timing_external_intelligence_ms`
  - `timing_persistence_ms`
  - `timing_llm_ms`（仅真实走 LLM 时写入）

## 4. 当前场景算例

### 场景 A：正常转账
- 输入：
  - `semantic_summary = "收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。"`
  - 常用城市
  - 低金额
- 预期：
  - `c_match` 偏低
  - `flag_s` 偏低
  - `f_final < 0.3`
  - 路由 `pass`

### 场景 B：中风险异地大额
- 输入：
  - 异地
  - `amount >= 5000`
  - 未明确命中高危短语
- 预期：
  - `flag_s` 中高
  - `g_dynamic` 中等
  - `0.3 <= f_final <= 0.8`
  - 路由 `interrogate`

### 场景 C：高危安全账户诈骗
- 输入：
  - `semantic_summary` 命中“安全账户”“验证码”
  - 或外部情报命中高危对象
- 预期：
  - `hard_block = True`
  - `final_risk = 1.0`
  - 路由 `block`

### 场景 D：二次质询红旗阻断
- 输入：
  - `user_reply = "警察让我转的"` 或 `"客服说验证资金后退款"`
- 预期：
  - 命中 `semantic_red_flags`
  - `secondary_decision = block_secondary`
  - 写入 `trace_events.secondary_decided`

## 5. 当前代码实现位置

- 公式与阈值：
  - `server/app/services/risk_engine.py`
- `c_match` 导出：
  - `server/app/services/bank_host.py::_derive_c_match`
- 场景识别与否定语义：
  - `server/app/services/risk_knowledge_base.py`
- 二次质询语义结果：
  - `server/app/services/agent_service.py`
- 审计事件：
  - `server/app/repositories/banking.py`
  - `server/app/services/bank_host.py`

## 6. 时延目标与来源

### 6.1 目标值
- `precheck hot path <= 750ms`
- `deterministic risk decision subpath <= 300ms`
- `secondary-check avg <= 3s`
- `LLM path P95 <= 30s`

### 6.2 推导依据
- `750ms = 3 x 250ms`
  - 参考公开实时支付欺诈决策 `under 250 milliseconds`
  - 来源：Unit21
- `300ms = 3 x 100ms`
  - 参考公开授权风险评分 `under 100 ms`
  - 来源：FraudNet
- `3s = 3 x 1s`
  - 参考 NN/g 对“用户思路不中断”的 `1 second`
- `30s = 3 x 10s`
  - 参考 NN/g 对“注意力保持”的 `10 seconds`

### 6.3 公开参考链接
- Unit21: `https://www.unit21.ai/products/real-time-payment-fraud-prevention`
- FraudNet: `https://www.fraud.net/solutions/transaction-monitoring`
- NN/g: `https://www.nngroup.com/articles/response-times-3-important-limits/`

### 6.4 当前项目的工程结论
- 当前 `precheck` 实测：
  - `cold_start avg/p95 40.35ms`
  - `warm_path avg 32.41ms`
  - `warm_path p95 58.19ms`
- 当前 `secondary-check` 实测：
  - `cold_start avg/p95 118.03ms`
  - `warm_path avg 46.66ms`
  - `warm_path p95 91.62ms`
- 当前结论：
  - `precheck warm_path p95` 已在目标内
  - `secondary-check avg` 已在目标内
- 当前 LLM benchmark 状态：
  - isolated LLM path benchmark：`avg 4536.54ms / p95 5784.39ms`
  - precheck all-Agent shadow benchmark：`avg 1837.33ms / p95 2094.15ms / drift 0.0`
- 在采样结果证明之前，不允许把 `precheck` 切为 mandatory Agent 热路径。

## 7. 全走 Agent 的判定结论

- 当前 `secondary-check` 的 LLM 调用是同步阻塞调用。
- 默认 `LLM_TIMEOUT_SECONDS = 2.0`。
- benchmark 独立使用 `LLM_BENCHMARK_TIMEOUT_SECONDS = 30.0`。
- 如果 `precheck` 也全走 Agent，则：
  - 增加外部网络依赖
  - 增加热路径不确定性
  - 增加不可用时的主链路失败概率
- 所以当前只允许：
  - `secondary-check` 使用 Agent
  - `precheck` 维持知识库+规则引擎
  - `precheck all-Agent` 只做 shadow benchmark

---

更新日期：2026-04-08  
定位：`公式与数据流文档`
