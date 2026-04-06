# Flutter Demo Client

Flutter 客户端负责展示手机银行演示界面，并把所有风控与 Agent 请求统一转发给 FastAPI 后端。

## 当前界面能力

- 首页资产卡片与演示入口
- 转账预检与二次质询弹窗
- 账单弹窗展示
- AI 助手弹窗

## 后端地址

通过 `API_BASE_URL` 配置：

Android 模拟器：

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Web/Desktop：

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## 说明

- Flutter 客户端不保存模型 Key。
- 所有 Agent 编排、风险分类、二次拦截判断都在后端完成。
- `风险演示` 快捷入口默认预填 `小c / 8000 / 北京`，用于触发中风险二次质询。
- 手工测试场景统一参考 `../docs/risk-test-cases.md`。
