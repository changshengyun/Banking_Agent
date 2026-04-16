# 风控场景测试用例与触发方式

前端速查文档：`client_flutter/write.md`。

## 1. 使用原则

- 手工测试和 API 精确触发统一以本文件为准。
- 城市统一使用：`上海`、`北京`、`西安`。
- 人物统一使用：`小a`、`小b`、`小c`、`小d`、`小e`、`小f`。

## 2. 前置条件

- 后端服务已启动：`http://127.0.0.1:8000`
- Flutter 已连接到对应后端

后端启动示例：

```powershell
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. 场景总表

| 场景ID | 目标结果 | 收款人 | 金额 | 城市 | 关键语义 / 条件 | 推荐触发方式 |
|---|---|---|---:|---|---|---|
| S1 | `pass / low` | `小b` | `300` | `上海` | 已知收款人 + 小额 | UI |
| S2 | `interrogate / medium` | `小c` | `8000` | `北京` | 异地 + 新收款人 + 中大额 | UI |
| S3 | `interrogate / medium` | `小d` | `6000` | `西安` | `临时借钱 / 马上转` | API |
| S4 | `block / high` | `小e` | `2000` | `上海` | `safe account / verification code` | API |
| S5 | `block / high` | `小f` | `20000` | `北京` | 高风险行为特征 + 中风险语义叠加 | API |
| S6 | `confirm` 失败 | 复用 S4/S5 | - | - | 对 `block` 的 token 调用确认 | API |

## 4. UI 手工触发

### S1：低风险直接放行

1. 首页点击 `转账`。
2. 输入：收款人 `小b`，金额 `300`，城市 `上海`。
3. 点击 `提交预检`。
4. 预期：提示可以继续转账，确认后成功。

### S2：中风险进入二次质询

1. 首页点击 `风险演示`，或手动输入：收款人 `小c`，金额 `8000`，城市 `北京`。
2. 点击 `提交预检`。
3. 预期：弹出二次质询对话框。
4. 对话框中应列出以下核验点：
   - 你与收款人的关系
   - 本次转账用途
   - 是否涉及验证码、安全账户、屏幕共享

建议输入一条标准化低风险说明：

```text
收款人是小c，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码、安全账户或屏幕共享。
```

预期：二次校验通过，可继续确认转账。

## 5. API 精确触发

下面命令可直接在 PowerShell 执行。

```powershell
$base = 'http://127.0.0.1:8000/api/v1/transfers/precheck'

# S3: 中风险语义 -> interrogate
$body3 = @{
  payee_name = '小d'
  amount = 6000
  context = @{
    session_id = 'manual-s3'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '西安'
    lat = 34.3416
    lng = 108.9398
    recent_page = 'home'
    last_action = 'tap_transfer'
    semantic_summary = '对方说临时借钱让我马上转。'
  }
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body $body3

# S4: 高风险关键词 -> block
$body4 = @{
  payee_name = '小e'
  amount = 2000
  context = @{
    session_id = 'manual-s4'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '上海'
    lat = 31.2304
    lng = 121.4737
    recent_page = 'home'
    last_action = 'tap_transfer'
    semantic_summary = '对方要求我把钱转到safe account，并把verification code发给他。'
  }
} | ConvertTo-Json -Depth 6
$r4 = Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body $body4
$r4

# S5: 高风险行为信号 + 语义叠加 -> block
$body5 = @{
  payee_name = '小f'
  amount = 20000
  context = @{
    session_id = 'manual-s5'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '北京'
    lat = 39.9042
    lng = 116.4074
    recent_page = 'message'
    last_action = 'copy_paste'
    semantic_summary = '这是临时退款，请马上处理。'
    input_pause_count = 8
    input_duration_ms = 900
    extra_signals = @{
      paste_count = 1
      app_switch_count = 2
    }
  }
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body $body5
```

## 6. 二次质询接口单独测试

```powershell
$precheckBody = @{
  payee_name = '小c'
  amount = 8000
  context = @{
    session_id = 'manual-secondary'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '北京'
    lat = 39.9042
    lng = 116.4074
    recent_page = 'home'
    last_action = 'tap_transfer'
    semantic_summary = '普通转账需求。'
  }
} | ConvertTo-Json -Depth 6

$precheck = Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body $precheckBody
$precheck

$secondaryBody = @{
  confirmation_token = $precheck.confirmation_token
  user_reply = '收款人是小c，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码、安全账户或屏幕共享。'
  context = @{
    session_id = 'manual-secondary'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '北京'
    lat = 39.9042
    lng = 116.4074
    recent_page = 'transfer'
    last_action = 'secondary_check'
    semantic_summary = '用户在二次质询阶段提交说明。'
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/transfers/secondary-check' -ContentType 'application/json' -Body $secondaryBody
```

高风险回答反例：

```text
对方说这是安全账户，让我先转过去核验，稍后会退回。
```

预期：二次校验应保持拦截或升级为拦截。

## 7. Block 后确认失败

```powershell
$confirmBody = @{ confirmation_token = $r4.confirmation_token } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/transfers/confirm' -ContentType 'application/json' -Body $confirmBody
```

预期：返回 HTTP `400`，提示该转账已被拦截，不能确认。

## 8. 自动化回归

```powershell
$env:PYTHONPATH=(Resolve-Path .).Path
server\.venv\Scripts\python -m pytest server\tests\test_api.py -q -p no:cacheprovider
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
```

Flutter：

```powershell
cd client_flutter
flutter analyze --no-version-check
flutter test --no-version-check
```

## 9. V2.3 外部情报命中样例

目标：验证 `external_intelligence` 已接入 `precheck / secondary-check / MCP`，并能在 XAI 面板展示 `external_intelligence` 节点。

推荐样例：

- 收款人：`小e`
- 金额：`300`
- 城市：`上海`
- 语义摘要：`正常生活转账。`

预期结果：

- `decision = block`
- `external_intelligence.status = hit`
- `external_intelligence.max_risk_level = high`
- `explain_pack.nodes` 包含 `external_intelligence`

PowerShell 触发示例：

```powershell
$bodyExternal = @{
  payee_name = '小e'
  amount = 300
  context = @{
    session_id = 'manual-v23-external'
    device_id = 'manual-device'
    platform = 'powershell'
    current_city = '上海'
    lat = 31.2304
    lng = 121.4737
    recent_page = 'home'
    last_action = 'tap_transfer'
    semantic_summary = '正常生活转账。'
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/transfers/precheck' -ContentType 'application/json' -Body $bodyExternal
```

MCP 工具验证：

- 工具名：`screen_external_intelligence`
- 入参：`payee_name = 小e`
- 预期：返回 `status = hit`
