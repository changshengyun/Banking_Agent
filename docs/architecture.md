# Banking AI Agent Demo Architecture

## Goal

This project is a demo-first banking mobile prototype. It focuses on two ideas:

- an AI agent that explains transfer risk-control decisions
- a complete Flutter + FastAPI + MCP demo architecture

## Components

- `client_flutter/`
  - Flutter UI shell
  - collects transfer context such as city, device id, page, and user action
  - sends all business requests to FastAPI
- `server/`
  - FastAPI app
  - main host/orchestration layer
  - SQLite-backed demo data store
  - risk rules and chat orchestration
- `mcp_servers/`
  - bank demo MCP server
  - outdoor knowledge MCP server

## Main Flow

1. Flutter starts a transfer and sends `payee_name`, `amount`, and `ClientContext`.
2. FastAPI loads account, transactions, common locations, and payee history.
3. The rule engine evaluates unusual city, large amount, new payee, and burst activity.
4. The host service builds an assistant message and returns `pass` or `review`.
5. If the decision is `review`, Flutter shows a confirmation dialog.
6. After confirmation, FastAPI commits the simulated transfer and refreshes balances.

## MCP Mapping

- `get_account_summary`
- `list_transactions`
- `get_user_profile`
- `get_common_locations`
- `precheck_transfer_risk`
- `commit_transfer`
- `answer_outdoor_question`
- `search_outdoor_knowledge`

## Demo Stability

- The default mode is `MOCK_LLM=true`.
- Risk decisions come from deterministic rules, not a remote model.
- The chat endpoint can still switch to a real compatible model if `LLM_API_KEY` and `LLM_MODEL` are set.

