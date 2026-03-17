# Demo Script

## Start Backend

1. Create a virtual environment with Python 3.13.
2. Install dependencies from `server/requirements.txt`.
3. Start FastAPI:

```powershell
py -3.13 -m uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Optional standalone MCP servers:

```powershell
py -3.13 -m mcp_servers.bank_server
py -3.13 -m mcp_servers.outdoor_server
```

## Start Flutter

Use a backend URL that matches the runtime:

- Android emulator: `http://10.0.2.2:8000`
- Web/Desktop: `http://127.0.0.1:8000`

Example:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Demo Sequence

1. Open the home page and show dashboard data from the backend.
2. Click `风险演示 (Risk Demo)`.
3. Keep preset values: payee `小c`, amount `8000`, city `北京`.
4. Submit precheck and explain that the backend host aggregates context and applies rules.
5. Show the risk dialog and explain why the agent requests confirmation.
6. Confirm the transfer and show the updated account balance.
7. Open `AI Assistant` and ask:
   - `Check my balance`
   - `Why was this transfer flagged by risk control?`
   - `Give me one camping safety tip`

## Notes

- This is a demo system, not a production banking app.
- Model keys should only be configured on the backend.
- If online model credentials are unavailable, set `MOCK_LLM=true` to switch to local mock mode.
