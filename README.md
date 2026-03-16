# Banking AI Demo Monorepo

This repository contains a demo-first banking project built around an AI agent and MCP.

## Structure

- `client_flutter/`: Flutter mobile-style frontend
- `server/`: FastAPI backend, SQLite demo data, agent orchestration, tests
- `mcp_servers/`: bank and outdoor knowledge MCP servers
- `docs/`: architecture notes and demo script

## Quick Start

1. Install backend dependencies:

```powershell
server\.venv\Scripts\python -m pip install -r server\requirements.txt
```

2. Start the backend:

```powershell
server\.venv\Scripts\python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

3. Run the Flutter client:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

For more detail, see [docs/demo-script.md](docs/demo-script.md).
