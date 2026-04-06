# Demo Script

## 启动后端

```powershell
py -3.13 -m venv server\.venv
server\.venv\Scripts\python -m pip install -r server\requirements.txt
server\.venv\Scripts\python -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

可选检查：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## 启动 Flutter

Android 模拟器：

```powershell
cd client_flutter
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Web/Desktop：

```powershell
cd client_flutter
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## 推荐演示顺序

1. 首页展示资产卡片和演示入口。
2. 点击 `转账`，输入低风险样例：`小b / 300 / 上海`，演示直接放行。
3. 点击 `风险演示`，触发中风险样例：`小c / 8000 / 北京`。
4. 展示二次质询弹窗，说明前端已标准化追问内容：
   - 与收款人的关系
   - 本次转账用途
   - 是否涉及验证码、安全账户、屏幕共享
5. 输入一条合理说明，演示 `/api/v1/transfers/secondary-check` 放行。
6. 再用 `docs/risk-test-cases.md` 里的 API 样例触发 `block`，演示硬拦截不可确认。
7. 打开 `AI 助手`，演示：
   - `帮我查一下余额`
   - `为什么刚才触发风控提醒`
8. 点击 `账单`，确认账单以弹窗而不是首页列表方式展示。

## 演示说明

- 这是答辩/MVP 演示系统，不是生产银行系统。
- 模型密钥只配置在后端。
- 当前所有 Agent 回复都依赖在线 OpenAI 兼容接口，不再提供本地模板回答切换。
- 精确风险触发方式统一维护在 `docs/risk-test-cases.md`。
