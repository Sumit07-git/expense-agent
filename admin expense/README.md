# Ledgerline — Ambient Expense Agent

An agentic expense-processing app: employees describe an expense in plain language to a chat agent, low-value expenses are auto-approved instantly, and higher-value ones are routed to a human admin for approval — all backed by [Google ADK](https://adk.dev/), Firebase, and a small custom frontend.

## What it does

1. An employee describes an expense in chat (e.g. *"I spent ₹4500 on a client dinner"*).
2. The agent parses it into structured data (amount, currency, category, description, date).
3. The expense is routed based on a USD-equivalent review threshold: low-value expenses are **auto-approved**, higher-value ones are flagged for **human review**.
4. A security checkpoint scans the description for prompt-injection attempts and redacts obvious PII (SSNs, credit card numbers) before anything is shown to a human.
5. Expenses needing review appear live in the **Admin Portal**, where an authorized admin approves or rejects them.
6. The employee sees the outcome — auto-approval, or the admin's decision — reflected live in their own submission history.

## Architecture

```
                        ┌──────────────────┐
   user message ───────▶│ smart_parse_input │
                        └─────────┬─────────┘
                  STRUCTURED      │      NATURAL_LANGUAGE
                        │         │         │
                        │         ▼         │
                        │  ┌─────────────┐  │
                        │  │intake_agent │◀─┘
                        │  │ (LLM)       │
                        │  └──────┬──────┘
                        └─────────┼──────────┘
                                  ▼
                          ┌───────────────┐
                          │route_by_amount │  ← USD-normalized threshold check
                          └───────┬────────┘
                AUTO_APPROVE      │      NEEDS_REVIEW
                       │          │          │
                       ▼          │          ▼
                ┌────────────┐    │  ┌────────────────────┐
                │auto_approve│    │  │ security_checkpoint │
                └────────────┘    │  │ (PII redaction +    │
                                   │  │  injection regex)   │
                                   │  └──────────┬──────────┘
                                   │       CLEAN │ FLAGGED
                                   │             │     │
                                   │             ▼     │
                                   │     ┌──────────────┐
                                   │     │ review_agent │
                                   │     │ (LLM)        │
                                   │     └──────┬───────┘
                                   │             │
                                   ▼             ▼
                          ┌──────────────────────┐
                          │   request_approval     │ ◀── human-in-the-loop (Admin Portal)
                          └───────────┬────────────┘
                                      ▼
                          ┌──────────────────────┐
                          │   process_decision     │
                          └────────────────────────┘
```

Implemented as a `google.adk.Workflow` graph (`expense_agent/agent.py`), not one big ReAct loop — each stage is an explicit, individually testable node, and the security-critical logic (thresholds, PII redaction, injection detection) lives in deterministic Python code that an attacker's free-text input can't influence, rather than being buried in a single prompt.

## System components

| Piece | What it is | Where |
|---|---|---|
| Agent backend | ADK workflow + FastAPI server, serves `/run_sse`, `/apps/...`, and the frontend itself at `/ui/` | `expense_agent/` |
| Employee UI | Chat interface to submit expenses + live submission history | `frontend/index.html`, `frontend/js/app.js` |
| Admin UI | Live review queue, approve/reject with confirmation | `frontend/admin.html`, `frontend/js/admin.js` |
| Auth | Firebase Authentication (Google sign-in) | `frontend/js/auth.js` |
| Data store | Firebase Firestore — `pending_expenses` collection holds every submitted expense (auto-approved and reviewed alike) | `frontend/firestore.rules` |
| Agent session store | SQLite (`sessions.db`), via ADK's `DatabaseSessionService` — keeps a submitter's paused conversation alive until an admin decides, surviving server restarts | `expense_agent/fast_api_app.py` |

## Security model

`security_checkpoint` is the main defense against prompt injection and PII leakage:

- **PII redaction** — SSNs and credit card numbers matching common formats are redacted before being logged or shown to a reviewer.
- **Injection detection** — regex patterns catch common injection phrasing (e.g. "ignore previous instructions", "bypass review"). Matches are logged and routed to manual approval with an explicit warning rather than silently passed through.

**Known limitation:** this detector is pattern-based, not semantic — a paraphrased or socially-engineered attempt can slip through as `CLEAN`. This gap is tracked explicitly in `tests/unit/test_workflow_nodes.py` and the adversarial cases in `tests/eval/datasets/basic-dataset.json`, rather than hidden. A natural next step is a second, LLM-based classification pass for descriptions that clear the regex check.

**Known limitation (currency):** the review threshold converts every amount to a USD-equivalent using a small static exchange-rate table in `agent.py` (`USD_EXCHANGE_RATES`) before comparing it to `config.review_threshold`. These rates are hardcoded approximations, not live — update them periodically, or swap in a live FX API for real financial accuracy.

## Project structure

```
admin expense/
├── expense_agent/
│   ├── agent.py              # Workflow graph: parsing, routing, security, review, approval
│   ├── config.py             # Model + review threshold configuration
│   ├── fast_api_app.py       # FastAPI app: ADK backend + persistent sessions + serves /ui
│   └── app_utils/            # Telemetry and shared utilities
├── frontend/
│   ├── index.html            # Employee chat UI
│   ├── admin.html            # Admin review dashboard
│   ├── js/                   # app.js (employee), admin.js (admin), auth.js, firebase-config.js
│   ├── css/
│   └── firestore.rules       # Security rules — admin email allowlist lives here
├── tests/
│   ├── unit/                 # Fast, no-LLM tests of the workflow's pure-function nodes
│   ├── integration/          # End-to-end tests via the ADK Runner
│   └── eval/                 # LLM-graded eval cases, including adversarial injection cases
├── Dockerfile                 # Builds + runs the whole app as one container (see Deployment)
├── .dockerignore
├── .github/workflows/keep-alive.yml  # Pings the deployed URL so it doesn't idle-sleep
└── pyproject.toml / uv.lock / requirements.txt
```

## Requirements

- **uv** — Python package manager: [Install](https://docs.astral.sh/uv/getting-started/installation/)
- A **Google AI Studio** API key (free tier): https://aistudio.google.com/apikey
- A **Firebase project** with Authentication (Google sign-in) and Firestore enabled

## Local setup

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Create `.env` in the project root:
   ```
   GOOGLE_API_KEY=your_key_here
   ```
3. Fill in Firebase config and admin emails in `frontend/js/firebase-config.js`:
   ```js
   const ADMIN_EMAILS = ["your-admin-email@example.com"];
   ```
   **Important:** also add the same email(s) to `frontend/firestore.rules` (the `allow read, update` block) — the JS list controls the UI, the rules file controls actual data access. Both must match.
4. Deploy the Firestore rules once (requires [Firebase CLI](https://firebase.google.com/docs/cli)):
   ```bash
   cd frontend
   firebase login
   firebase use <your-firebase-project-id>
   firebase deploy --only firestore:rules
   ```
5. Run the app:
   ```bash
   make playground
   # or: uv run uvicorn expense_agent.fast_api_app:app --host 127.0.0.1 --port 8080
   ```
6. Open `http://127.0.0.1:8080/ui/` — sign in as an employee to submit an expense, or as an admin (email from `ADMIN_EMAILS`) to review the queue.

## Testing

```bash
uv run pytest tests/unit -v          # fast, no LLM calls, no credentials needed
uv run pytest tests/integration -v   # full agent run via the ADK Runner
```

## Deployment

This app is designed to deploy as **one container** — the same FastAPI app serves the backend API *and* the static frontend from `/ui/`, so there's no separate frontend hosting or CORS setup needed.

Recommended: **Hugging Face Spaces** (free, Docker-based, no credit card required).

1. Create a Space at https://huggingface.co/new-space with **SDK: Docker**.
2. Add your key as a secret: Space **Settings → Variables and secrets** → `GOOGLE_API_KEY`.
3. Push this project to the Space's git remote (the included `Dockerfile` handles the rest):
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
   git push --force space main
   ```
4. Once it's **Running**, open `https://YOUR_USERNAME-YOUR_SPACE.hf.space/ui/`.
5. Add that domain to Firebase Console → Authentication → Settings → **Authorized domains**.
6. Set up a free keep-alive ping (e.g. [UptimeRobot](https://uptimerobot.com), every 5 min) hitting the `/ui/` URL — free Spaces sleep after 48h of no traffic; a periodic ping keeps it always warm. The included `.github/workflows/keep-alive.yml` does the same thing via GitHub Actions if you prefer.

`SESSION_DB_URL` env var can point `fast_api_app.py` at a real Postgres instance instead of the default local SQLite file, if you need agent sessions to survive a full container rebuild (not just a restart/sleep).

## Observability

Structured JSON logs for security alerts and approval/rejection decisions (see `emit_expense_alert` and the logging calls in `agent.py`) — useful for building dashboards on auto-approval rate, average review turnaround, or injection-attempt frequency.
