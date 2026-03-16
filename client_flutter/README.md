# Flutter Demo Client

This Flutter app is the demo frontend for the banking AI agent project.

## What It Shows

- dashboard data loaded from FastAPI
- transfer precheck and risk-review dialog
- simulated transfer confirmation
- AI assistant chat for balance, bills, risk explanation, and outdoor knowledge

## Backend URL

Configure the backend with `API_BASE_URL`.

- Android emulator:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

- Web or desktop:

```powershell
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Notes

- The client no longer stores any model key.
- All agent orchestration lives on the backend.
- The `风险演示` shortcut prefills a high-risk transfer scenario for presentations.
