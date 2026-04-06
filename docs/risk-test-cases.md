# 风控场景测试用例与触发方式

## 1. 前置条件
- 后端服务已启动：`http://127.0.0.1:8000`
- 启动命令示例：

```powershell
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

## 2. 场景清单（建议答辩顺序）

| 场景ID | 目标结果 | 核心条件 | 推荐触发方式 |
|---|---|---|---|
| S1 | `pass / low` | 常用城市 + 已知收款人 + 小额 | UI 或 API |
| S2 | `interrogate / medium` | 异地 + 新收款人 + 中大额 | UI 或 API |
| S3 | `interrogate / medium` | 语义里出现“临时/马上/借钱”等中风险词 | API |
| S4 | `block / high` | 语义里出现 `safe account`、`verification code` 等高风险词 | API |
| S5 | `block / high` | 静态高风险 + 行为高风险 + 中风险语义叠加，综合分超阈值 | API |
| S6 | 已拦截不可确认 | 对 S4/S5 的 token 调用 confirm，返回 400 | API |

## 3. UI 触发方法（手工）

### S1：低风险放行
1. 首页点击 `转账`。
2. 输入：收款人 `小b`，金额 `300`，城市 `上海`。
3. 点击 `提交预检`。
4. 预期：提示可继续转账，确认后成功。

### S2：中风险补充确认
1. 首页点击 `转账` 或 `风险演示`。
2. 输入：收款人 `小c`，金额 `8000`，城市 `北京`。
3. 点击 `提交预检`。
4. 预期：弹窗显示“需要补充确认 · 中风险”。

说明：当前默认 UI 流程里 `semantic_summary` 是固定文案，通常不会直接触发硬拦截（`block`），`block` 建议用 API 精准触发。

## 4. API 触发方法（精确复现）

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
    current_city = '上海'
    lat = 31.2304
    lng = 121.4737
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
    semantic_summary = '请转到safe account并提供verification code。'
  }
} | ConvertTo-Json -Depth 6
$r4 = Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body $body4
$r4

# S6: block 后确认应失败(HTTP 400)
$confirmBody = @{ confirmation_token = $r4.confirmation_token } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/transfers/confirm' -ContentType 'application/json' -Body $confirmBody
```

## 5. 自动化触发（回归测试）

```powershell
$env:PYTHONPATH=(Resolve-Path .).Path
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -p no:cacheprovider
```

按单个场景筛选：

```powershell
$env:PYTHONPATH=(Resolve-Path .).Path
server\.venv\Scripts\python -m pytest server\tests\test_risk_scenarios.py -q -k block_high_hard_keyword -p no:cacheprovider
```
