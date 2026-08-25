# Deployment

This project uses Docker Compose for both local development and production.

## Local Docker

Copy the local example to `.env`:

```powershell
copy .env.local.example .env
```

Set at least one LLM key in `.env`, for example `GROQ_API_KEY`.

Start the stack with the local compose file:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

`docker-compose.local.yml` sets:

- `VITE_API_BASE_URL=http://localhost:8000`
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- `ENVIRONMENT=development`
- `DEBUG=true`

Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`

Run a manual summary refresh:

```powershell
$apiKey = (Get-Content .env | Where-Object { $_ -match '^API_AUTH_KEY=' } | Select-Object -First 1) -replace '^API_AUTH_KEY=', ''
$headers = @{ "X-API-Key" = $apiKey }
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/trigger/summary?time_of_day=manual&refresh=true" -Headers $headers
```

## Production With Dokploy

Use Dokploy's Docker Compose deployment and keep:

```text
Compose Path: ./docker-compose.yml
```

Do not point Dokploy at `docker-compose.local.yml`; that file is only for local development.

In Dokploy, configure environment variables using `.env.prod.example` as the reference. Required production values:

```env
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://ecobriefbolivia.online,https://briefs.ecobriefbolivia.online
VITE_API_BASE_URL=https://ecobriefbolivia.online
GROQ_API_KEY=...
NEWS_API_KEY=...
API_AUTH_KEY=...
POSTGRES_PASSWORD=...
```

`VITE_API_BASE_URL` is a frontend build argument. If you change it in Dokploy, rebuild the frontend image.

Database migrations run automatically during backend startup. Before deploying schema changes,
take a database backup from the VPS provider or Postgres volume. Migration rules are documented
in `migrations/README.md`.

Manual summary refresh can run synchronously or asynchronously. Cron keeps using the synchronous
default. For UI/manual operations that may hit proxy timeouts, use:

```text
POST /trigger/summary?time_of_day=manual&refresh=true&async_mode=true
GET /trigger/summary/jobs/{job_id}
```

The cron container uses Docker's internal network:

```env
BACKEND_BASE_URL=http://backend:8000
```

That value is defined directly in `docker-compose.yml` because the backend and cron services run in the same Compose project.

## Distribution Channels (Email / WhatsApp / Telegram)

Each channel degrades independently: if it's not configured, `/api/preferences/options`
reports it as unavailable in the subscribe form and sends silently fail (logged, not
raised) rather than breaking delivery for other channels.

**Email** — set `EMAIL_ENABLED=true` and `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM_EMAIL`.
With Gmail, use an App Password, not the account password, and rotate it if it was ever
committed or shared. Gmail can rate-limit or spam-flag bulk sends without SPF/DKIM on a
custom domain — consider a transactional provider (SES, Postmark, Resend) before scaling
past a handful of daily subscribers.

**WhatsApp** — set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, and
point the Twilio WhatsApp sender's webhook at `https://<domain>/webhook/whatsapp`. Twilio's
WhatsApp sandbox only reaches numbers that manually joined it — for real subscribers you
need a Meta-approved WhatsApp Business sender, which requires business verification and
approved message templates for anything sent outside a 24h user-initiated window. There is
no "send to a WhatsApp group" API on the WhatsApp Business Platform — only one-to-one
messages to opted-in numbers, which is what `send_daily_summary` already does per
subscriber (a broadcast list, not a group).

**Telegram** — set `TELEGRAM_BOT_TOKEN` (from @BotFather) and `TELEGRAM_WEBHOOK_URL` to
the backend's public HTTPS origin (no path — the app appends `/webhook/telegram` and
registers the webhook with Telegram on startup). Set `TELEGRAM_WEBHOOK_SECRET` to a random
string too; the app validates it on every incoming webhook request, which stops anyone who
guesses the URL from injecting fake updates (fake unsubscribes, etc.). Telegram requires a
valid HTTPS certificate on the webhook URL — a Dokploy/Traefik-issued Let's Encrypt cert on
the domain satisfies this.

## URL Rules

Use local URLs only in local development:

```env
VITE_API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Use public HTTPS URLs in production:

```env
VITE_API_BASE_URL=https://ecobriefbolivia.online
CORS_ORIGINS=https://ecobriefbolivia.online,https://briefs.ecobriefbolivia.online
```

If the API is deployed under a separate subdomain, set both values explicitly:

```env
VITE_API_BASE_URL=https://api.ecobriefbolivia.online
CORS_ORIGINS=https://ecobriefbolivia.online,https://briefs.ecobriefbolivia.online
```
