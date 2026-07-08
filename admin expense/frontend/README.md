# Ledgerline — frontend for ambient-expense-agent

A standalone HTML/CSS/JS frontend (no build step) with Firebase Authentication,
wired to talk to the `expense_agent` FastAPI/ADK backend in this repo.

## What's here

```
frontend/
├── index.html          # auth gate + app shell (single page, no router needed)
├── css/styles.css       # design system (dark security-console theme)
└── js/
    ├── firebase-config.js   # your Firebase project keys + backend URL
    ├── auth.js               # email/password + Google sign-in, signup, reset
    └── app.js                 # composer, ledger sidebar, pipeline stepper, ADK calls
```

## 1. Set up Firebase Authentication

1. Create a project at https://console.firebase.google.com (or reuse one).
2. Project settings → General → "Your apps" → add a Web app → copy the config object.
3. Paste those values into `js/firebase-config.js` (`firebaseConfig`).
4. Authentication → Sign-in method → enable **Email/Password** and **Google**.
5. Authentication → Settings → Authorized domains → add `localhost` and whatever
   domain you deploy the frontend to.

## 2. Run frontend + backend together (recommended)

`fast_api_app.py` now mounts this `frontend/` folder directly at `/ui`, so
the frontend and the API are served from the **same origin**. This avoids
CORS entirely, and sidesteps browser-extension/shield issues (Brave Shields,
some ad-blockers, and strict tracker-protection settings are known to
interfere with cross-origin `fetch()` calls between two localhost ports
even when CORS headers are correct).

```bash
cd ambient-expense-agent
uv run python -m expense_agent.fast_api_app
```

Then open:

```
http://127.0.0.1:8080/ui/
```

Leave `BACKEND_URL: ""` in `js/firebase-config.js` — an empty string means
"same origin as this page," so no separate static server is needed.

### If you must serve the frontend separately (different host/port)

Set `BACKEND_URL` to an absolute URL instead, e.g.:

```js
const BACKEND_CONFIG = {
  BACKEND_URL: "http://127.0.0.1:8080",
  APP_NAME: "expense_agent",
};
```

CORS is already enabled on the backend (`CORSMiddleware`, configurable via
the `FRONTEND_ORIGINS` env var). If it's still showing "Offline demo":

- Open DevTools → Console/Network and look at the actual failed request —
  the frontend now toasts the real error instead of failing silently.
- **Brave**: click the Shields icon on the page and try "Shields down" for
  this site, or check Settings → Privacy and security → no aggressive
  fingerprint/tracker blocking is catching `127.0.0.1`/`localhost` fetches.
  Using the same-origin `/ui` setup above removes this risk entirely.
- Make sure the URL you type in the browser and `BACKEND_URL` use the exact
  same hostname (`127.0.0.1` and `localhost` are different origins to the
  browser, even though they resolve to the same machine).
- Confirm the backend is actually reachable: `curl http://127.0.0.1:8080/list-apps` (or similar) from a terminal.

## Design notes

- Palette, type (Space Grotesk / Inter / JetBrains Mono) and the signature
  "pipeline stepper" element are all derived from the project's own
  architecture (`Parse → Route → Security → Review → Decision`), not a
  generic template.
- Currency selection mirrors the picker already injected by
  `fast_api_app.py`'s `CURRENCY_INJECTION_SCRIPT`, and is sent the same way:
  prefixed as `[Currency: XXX]` on the outgoing message.
- Sidebar ledger and decision cards use lightweight client-side parsing of
  the agent's reply text to color status chips (auto-approved / needs review
  / flagged) — swap in structured fields from your agent's response schema
  for a production build instead of the keyword heuristic in `statusFromText`.
