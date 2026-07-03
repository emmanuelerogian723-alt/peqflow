# FlowMind — AI Automation Engine

**Describe what you want to automate in plain English. FlowMind builds it, runs it 24/7, and gives you a dashboard to monitor everything.**

## What It Does

Instead of manually configuring Zapier workflows, you just type:

> "When someone pays on Paystack, send them a WhatsApp receipt and add them to Google Sheets"

FlowMind parses your description, creates a structured workflow, and runs it automatically.

## Architecture

```
flowmind/
├── backend/
│   ├── app/
│   │   ├── api/routes.py        # REST API (13 endpoints)
│   │   ├── core/config.py       # Settings & integration registry
│   │   ├── engine/
│   │   │   ├── parser.py        # NL → structured workflow parser
│   │   │   └── runner.py        # Workflow execution engine
│   │   ├── integrations/
│   │   │   ├── paystack.py      # Payment integration
│   │   │   ├── whatsapp.py      # WhatsApp Business API
│   │   │   ├── gmail.py         # Gmail OAuth2
│   │   │   ├── slack.py         # Slack Web API
│   │   │   ├── notion.py        # Notion API
│   │   │   ├── google_sheets.py # Google Sheets API
│   │   │   └── telegram.py      # Telegram Bot API
│   │   ├── mcp_server/server.py # MCP server for Claude integration
│   │   └── main.py              # FastAPI entry point
│   ├── static/dashboard.html    # Web dashboard
│   └── requirements.txt
├── desktop/                     # Electron desktop app
│   ├── main.js                  # Electron main process
│   ├── preload.js               # Secure IPC bridge
│   ├── renderer/index.html      # Dashboard UI
│   └── package.json
└── render.yaml                  # Render deployment config
```

## Integrations (8 ready)

1. **Paystack** — payments, subscriptions, refunds
2. **WhatsApp Business** — messages, templates, images, documents
3. **Gmail** — send, reply, label
4. **Google Sheets** — append, update, read
5. **Slack** — messages, DMs, channels
6. **Notion** — pages, databases
7. **Telegram** — messages, photos, documents
8. **Shopify** — orders, customers, inventory

## MCP Server

FlowMind exposes 12 MCP tools so Claude (or any MCP-compatible AI) can:
- Create automations from natural language
- List, activate, pause, delete workflows
- Execute workflows manually
- Test integrations
- Get execution history

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "flowmind": {
      "command": "python3",
      "args": ["/path/to/flowmind/backend/app/mcp_server/server.py"],
      "env": {
        "PAYSTACK_SECRET_KEY": "your_key",
        "WHATSAPP_TOKEN": "your_token"
      }
    }
  }
}
```

## API Endpoints

- `POST /api/v1/workflows/parse` — Parse NL to workflow
- `POST /api/v1/workflows/create` — Parse + save workflow
- `GET /api/v1/workflows` — List all workflows
- `GET /api/v1/workflows/{id}` — Get workflow
- `DELETE /api/v1/workflows/{id}` — Delete workflow
- `POST /api/v1/workflows/activate` — Activate workflow
- `POST /api/v1/workflows/pause` — Pause workflow
- `POST /api/v1/workflows/execute` — Execute workflow
- `GET /api/v1/workflows/{id}/history` — Execution history
- `GET /api/v1/integrations` — List integrations
- `GET /api/v1/integrations/capabilities` — Capability registry
- `POST /api/v1/integrations/test` — Test integration
- `POST /api/v1/webhooks/paystack` — Paystack webhook
- `POST /api/v1/webhooks/whatsapp` — WhatsApp webhook
- `GET /api/v1/webhooks/whatsapp` — WhatsApp verify
- `GET /api/v1/health` — Health check

## Deployment

```bash
# Local
cd backend && python3 app/main.py

# Docker
docker build -t flowmind . && docker run -p 8000:8000 flowmind

# Render
# Connect repo, deploy with render.yaml
```

## License
Proprietary — MUTYINT (c) 2026
