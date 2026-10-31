# FinCoach

Educational personal-finance app for students, first-job professionals, and gig workers in India. It helps you map income and expenses, keep a flexible budget, learn investing *concepts*, and run **hypothetical** savings/SIP maths.

FinCoach is **not** a SEBI-registered adviser. It does **not** tell you which stock to buy, how much to invest, or place trades. Numbers on market screens are either live from a named provider or explicitly unavailable — never invented.

## What you need

- Python 3.11+
- Node.js 20+
- Optional providers (leave blank to see honest setup/disconnected states):
  - Twilio Verify (mobile OTP)
  - OpenAI (Money Coach)
  - Angel One SmartAPI JWT (read-only holdings)
  - CoinGecko (Bitcoin; public, key optional)
  - gold-api.com (gold/silver spot; public)
  - ExchangeRate-API open endpoint (indicative USD/INR conversions; public)

## Setup

1. Copy environment placeholders (never commit a filled `.env`):

```bash
copy .env.example .env
```

On macOS/Linux: `cp .env.example .env`

2. Set `SESSION_SECRET` to a long random string. Keep Twilio, OpenAI, and Angel One values empty until you have real credentials.

3. Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

4. Frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** (use this host so the session cookie matches the Vite proxy).

The Vite dev server proxies `/api` to FastAPI on port 8001. Do not put API keys in frontend code. If port 5173 is occupied, Vite automatically selects the next available port.

## Provider configuration

All secrets are read by FastAPI from `.env` (project root or `backend/.env`).

| Variable | Purpose |
| --- | --- |
| `SESSION_SECRET` | Signs nothing itself; keep a strong secret for deployment hygiene |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID` | Real SMS OTP via [Twilio Verify](https://www.twilio.com/docs/verify/api). If missing, the login screen shows a setup state. **No fake OTP is generated.** |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Money Coach. If missing, replies are labeled **limited demo fallback**. |
| `ANGEL_ONE_API_KEY`, `ANGEL_ONE_CLIENT_CODE`, `ANGEL_ONE_JWT_TOKEN`, `ANGEL_ONE_REFRESH_TOKEN` | Read-only SmartAPI holdings. Tokens belong on the server. FinCoach **never** asks for Angel One or Groww passwords. |
| `COINGECKO_API_KEY` | Optional. Bitcoin quotes use the public CoinGecko simple price API. |
| `METALS_API_BASE` | Default `https://api.gold-api.com` (`/price/XAU`, `/price/XAG`). If the source fails, the UI says live prices are unavailable. |

USD equivalents for INR-denominated stock holdings and INR equivalents for USD-denominated metals use the public ExchangeRate-API open endpoint. The app displays its rate and provider timestamp; conversions are indicative, not executable exchange quotes. Bitcoin INR and USD quotes and their 24-hour movements come directly from CoinGecko. When a conversion or movement is unavailable, the UI says so instead of calculating with a stale or invented rate.

### Twilio Verify

Create a Verify service in Twilio, put the three values in `.env`, restart FastAPI, then use **Mobile OTP** on the login screen. Codes are checked only by Twilio through the backend.

### Angel One SmartAPI

Generate API key and JWT outside FinCoach (SmartAPI login / publisher). Paste **API key + JWT** (and refresh token if you have one) into `.env`. FinCoach only calls portfolio/quote-style read endpoints and will not place orders.

### Database

SQLite file `backend/fincoach.db` for the local MVP. SQLAlchemy models avoid SQLite-only SQL so you can later set `DATABASE_URL=postgresql+psycopg://…`.

## Tests and production frontend build

```bash
cd backend
.venv\Scripts\activate
pytest -q
```

```bash
cd frontend
npm run build
```

## Product notes

- **Overall P&L** = current value minus quantity × average purchase price.
- **Daily movement** = latest price minus previous close.
- SIP math always includes a **0% return** scenario. Returns are not guaranteed.
- Groww’s logged-in account page is not scraped. Platform text uses public, dated SEBI/NSE investor-education links only.

## Features that need live credentials (not verified in this environment)

These work as **setup / disconnected / fallback** states without secrets. They have **not** been verified against live vendor accounts in this workspace:

- Twilio Verify SMS send/check
- OpenAI Chat Completions
- Angel One SmartAPI holdings and token refresh
- CoinGecko (network-dependent; may work without a key)
- gold-api.com metals feed (network-dependent)
- ExchangeRate-API USD/INR conversion feed (network-dependent; USD equivalents are omitted if unavailable)
