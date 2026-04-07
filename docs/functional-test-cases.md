# Sentinel-Mobile 功能测试用例

本文档用于 Boss/产品/测试手工验收当前 `MVP V2` 的核心功能。

## 文件位置

- 功能测试用例文档：`docs/functional-test-cases.md`
- 风控场景测试文档：`docs/risk-test-cases.md`
- 后端自动化测试：`server/tests/`
- 前端自动化测试：`client_flutter/test/`

## 测试前置条件

- 后端已启动：`http://127.0.0.1:8000`
- Flutter 客户端已连接到本地后端
- 演示城市统一使用：`北京 / 上海 / 西安`
- 演示人物统一使用：`小a / 小b / 小c / 小d / 小e / 小f`

后端启动命令：

```powershell
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

## F-01 首页加载

- 目标：验证首页主框架、导航入口和资产卡片正常显示
- 步骤：
1. 启动客户端
2. 进入首页
- 预期结果：
1. 可看到首页主导航
2. 可看到风控入口、账单入口、AI 助手入口
3. 页面无报错、无空白

## F-02 账单弹窗展示

- 目标：验证账单不再以内嵌列表展示，而是弹窗展示
- 步骤：
1. 进入首页
2. 点击账单入口
- 预期结果：
1. 弹出账单窗口
2. 可看到账单记录
3. 可关闭弹窗并返回首页

## F-03 AI 助手弹窗展示

- 目标：验证 AI 助手可正常打开
- 步骤：
1. 进入首页
2. 点击 AI 助手入口
- 预期结果：
1. 弹出对话窗口
2. 输入框可编辑
3. 页面无异常

## F-04 低风险转账直接放行

- 目标：验证低风险场景走 `pass`
- 输入：
- 收款人：`小b`
- 金额：`300`
- 城市：`上海`
- 语义摘要：`日常生活转账。`
- 步骤：
1. 进入转账页面
2. 填入上述信息并提交预检
- 预期结果：
1. 预检结果为 `pass`
2. 风险等级为 `low`
3. 可进入确认转账流程

## F-05 中风险转账进入二次质询

- 目标：验证中风险场景走 `interrogate`
- 输入：
- 收款人：`小c`
- 金额：`8000`
- 城市：`北京`
- 语义摘要：`普通转账需求。`
- 步骤：
1. 提交预检
- 预期结果：
1. 预检结果为 `interrogate`
2. 风险等级为 `medium`
3. 弹出二次质询窗口
4. 界面展示解释面板

## F-06 高风险场景直接拦截

- 目标：验证高风险关键词触发 `block`
- 输入：
- 收款人：`小e`
- 金额：`2000`
- 城市：`上海`
- 语义摘要：`对方要求转到safe account并提供verification code。`
- 步骤：
1. 提交预检
- 预期结果：
1. 预检结果为 `block`
2. 风险等级为 `high`
3. 页面提示当前交易已被拦截

## F-07 Block 后禁止确认转账

- 目标：验证被拦截交易不能继续确认
- 前置：先执行 F-06
- 步骤：
1. 使用被拦截交易的 `confirmation_token` 调用确认接口或在前端继续确认
- 预期结果：
1. 返回失败
2. 提示该交易已被拦截，不能确认

## F-08 二次质询低风险解释通过

- 目标：验证合理补充说明可通过二次质询
- 前置：先触发 `interrogate`
- 建议回复：

```text
收款人是小c，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码、安全账户或屏幕共享。
```

- 预期结果：
1. 二次质询结果为 `pass_secondary`
2. 可继续确认转账
3. 解释面板仍正常显示

## F-09 二次质询命中警察转账红旗

- 目标：验证 patch-3 的语义红旗直拦
- 前置：先触发 `interrogate`
- 回复：

```text
警察让我转的，说现在就要打款。
```

- 预期结果：
1. 二次质询结果为 `block_secondary`
2. `semantic_red_flags` 非空
3. 包含 `司法机关要求转账`

## F-10 二次质询命中客服验证资金红旗

- 目标：验证退款/验证资金类红旗直拦
- 前置：先触发 `interrogate`
- 回复：

```text
客服说验证资金后退款，还要我先刷流水。
```

- 预期结果：
1. 二次质询结果为 `block_secondary`
2. `semantic_red_flags` 非空
3. 包含 `客服要求验证资金`

## F-11 二次质询无关回复不得放行

- 目标：验证回避性回复不会直接放行
- 前置：先触发 `interrogate`
- 回复：

```text
我就是想转账，别问了。
```

- 预期结果：
1. 二次质询结果不是 `pass_secondary`
2. 预期为 `interrogate`
3. `semantic_red_flags` 为空

## F-12 外部情报命中

- 目标：验证 `external_intelligence` 已接入主链路
- 输入：
- 收款人：`小e`
- 金额：`300`
- 城市：`上海`
- 语义摘要：`正常生活转账。`
- 步骤：
1. 提交预检
- 预期结果：
1. 返回 `external_intelligence`
2. 可看到 `external_intelligence` 节点或命中信息
3. 若命中名单，风险结果应上调或直接拦截

## F-13 XAI 解释面板完整性

- 目标：验证解释面板节点完整
- 步骤：
1. 触发一次 `interrogate` 或 `block`
2. 打开解释面板
- 预期结果：
1. 至少包含以下节点：
    - `static`
    - `behavior`
    - `semantic`
    - `external_intelligence`
    - `decision`
2. 每个节点包含标题、等级、摘要、分值

## 自动化测试现有位置

### 后端

- [test_api.py](e:/Projects/Banking_AI_Project/server/tests/test_api.py)
- [test_risk_scenarios.py](e:/Projects/Banking_AI_Project/server/tests/test_risk_scenarios.py)
- [test_patch2_secondary_followup.py](e:/Projects/Banking_AI_Project/server/tests/test_patch2_secondary_followup.py)

### 前端

- [widget_test.dart](e:/Projects/Banking_AI_Project/client_flutter/test/widget_test.dart)

## 推荐执行命令

### 后端

```powershell
$env:PYTHONPATH=(Get-Location).Path
server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_patch2_secondary_followup.py -q -p no:cacheprovider
```

### 前端

```powershell
cd client_flutter
flutter analyze --no-version-check
flutter test --no-version-check
```
