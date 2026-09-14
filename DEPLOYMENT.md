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
SITE_BASE_URL=https://ecobriefbolivia.online
GROQ_API_KEY=...
API_AUTH_KEY=...
POSTGRES_PASSWORD=...
```

`VITE_API_BASE_URL` is a frontend build argument. If you change it in Dokploy, rebuild the frontend image.

### Domain / path routing

`docker-compose.yml` has no Traefik labels -- unlike the AWS deployment (which uses a committed
Caddyfile, `deploy/aws/Caddyfile`), Dokploy's own domain routing is configured entirely in its UI,
one entry per path prefix, all pointing at the same domain(s) so the frontend and backend can share
one origin (this is what lets `VITE_API_BASE_URL` just be the bare domain instead of a separate API
subdomain). Mirror the same rules the AWS Caddyfile encodes -- most specific path first, frontend
catches whatever is left:

| Domain | Path | Service | Port |
|---|---|---|---|
| ecobriefbolivia.online (+ www, briefs) | `/api/*` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/admin/*` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/webhook/*` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/trigger/*` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/health` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/stats` | backend | 8000 |
| ecobriefbolivia.online (+ www, briefs) | `/` (catch-all) | frontend | 5173 |

Enable HTTPS on each domain entry (Dokploy provisions Let's Encrypt certs the same way Caddy does)
-- Telegram's webhook and any browser hitting the site both require valid HTTPS, not just a
listening port.

### Firewall

`docker-compose.yml` publishes `postgres`, `backend`, and `frontend` directly on the host (5433,
8000, 5173) -- needed for local dev (`localhost:8000`, etc.), but Dokploy's Traefik talks to
containers over the internal Docker network by service name, not through those published ports, so
none of the three need to be reachable from the internet in production. Unlike AWS (where the EC2
Security Group is a default-deny firewall you configure per-port at instance launch), a Hostinger VPS
has no such default -- every published port is open to the world until you close it yourself. Unless
Hostinger's own panel has an equivalent, lock it down with `ufw` on the box once Dokploy/Traefik is
confirmed working over 80/443:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

Do this only *after* verifying the site loads over HTTPS through Dokploy -- enabling `ufw` before
confirming that closes your only way in if something's misconfigured (SSH stays open here, but
double check that rule matches the actual SSH port before enabling).

### Telegram

Same bot as local testing (from @BotFather), pointed at the real domain instead of an ngrok tunnel:

```env
TELEGRAM_BOT_TOKEN=<same token from @BotFather>
TELEGRAM_WEBHOOK_URL=https://ecobriefbolivia.online
TELEGRAM_WEBHOOK_SECRET=<a random string you generate, e.g. `openssl rand -hex 32`>
```

Nothing else to configure manually: `_register_telegram_webhook` (`src/main.py`) calls Telegram's
`setWebhook` on every backend startup, pointed at `TELEGRAM_WEBHOOK_URL` + `/webhook/telegram`. As
long as the `/webhook/*` routing rule above is live and the domain has a valid cert, it registers
itself. Verify with `getWebhookInfo`:

```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

`SITE_BASE_URL` (same domain) is what the bot's `/noticias` "leer completo" links point at --
without it, that link is silently omitted from the card, not broken.

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

## Production on AWS EC2 (Free Tier)

The Hostinger/Dokploy deployment above is currently down, so this EC2 instance is the
sole production deployment, serving the apex domain directly (`ecobriefbolivia.online`,
plus `www` and `briefs`). It uses the same `docker-compose.yml`, plus
`docker-compose.aws.yml` to trim the backend to 2 gunicorn workers and add a small
Caddy container for automatic HTTPS (Dokploy/Traefik isn't used here — on a 1GiB
free-tier instance it alone would eat the RAM budget this needs for Postgres,
the backend, the frontend, and the cron job).

**EC2 over Lightsail:** EC2's free tier (a t2.micro/t3.micro instance, 750 hours/month,
1 GiB RAM) is the standard 12-month AWS Free Tier allocation. Lightsail has its own,
separate, and historically much shorter free trial, after which it bills a flat monthly
rate regardless of how much of the account's free-tier window is left — a real risk
for "I only want to spend the free trial." Check **Billing and Cost Management -> Free
Tier** in the AWS Console first to confirm which free-tier model applies to this
specific account before provisioning anything; the plan below assumes the standard
per-service free tier.

### 1. IAM (the non-root user)

In the IAM console, attach the AWS-managed policy **`AmazonEC2FullAccess`** to the
existing IAM user. This scopes it to EC2 only (instances, security groups, key pairs,
Elastic IPs, EBS volumes) — no S3, no IAM, no billing access. Sign in to the AWS
Console as that IAM user (not root) for every step below.

This IAM user/login is only for the AWS Console/CLI. It is unrelated to the SSH key
used to log into the instance itself (step 2) — don't conflate the two.

### 2. Launch the instance

1. EC2 console -> **Launch instance**.
2. AMI: **Ubuntu Server 22.04 LTS** (marked "Free tier eligible").
3. Instance type: whichever the console marks **Free tier eligible** (t2.micro or
   t3.micro depending on region) — 1 vCPU, 1 GiB RAM.
4. Key pair: **Create new key pair** (RSA, `.pem`), download it, keep it safe. This is
   what SSHes into the box — separate from the IAM login above.
5. Network settings -> create a new security group:
   - SSH (22) from **My IP** only, not Anywhere.
   - HTTP (80) from Anywhere (needed for the Let's Encrypt challenge and the
     redirect to HTTPS).
   - HTTPS (443) from Anywhere.
6. Storage: bump to 20 GiB gp3 (still inside the 30 GiB free tier) for Docker image
   layers.
7. Launch.

### 3. Elastic IP

Network & Security -> **Elastic IPs** -> Allocate -> Associate it with the new
instance. An Elastic IP is free only while attached to a *running* instance — if you
stop the instance long-term, either release the IP or expect a small hourly charge on
it.

### 4. First login and setup

```bash
chmod 400 path/to/key.pem
ssh -i path/to/key.pem ubuntu@<ELASTIC_IP>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version   # confirms the compose plugin is present
```

Get the code onto the box. For a private repo, generate a deploy key on the instance
and add it as a **read-only Deploy Key** on the GitHub repo (Settings -> Deploy keys)
rather than reusing a personal key:

```bash
ssh-keygen -t ed25519 -C "ec2-deploy" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub   # paste this into GitHub's Deploy keys
git clone git@github.com:Jhoshoa/news-summarizer.git
cd news-summarizer
```

Add swap before building anything — a 1GiB instance will OOM on `npm run build`
without it:

```bash
chmod +x deploy/aws/setup-swap.sh
./deploy/aws/setup-swap.sh
```

### 5. Configure secrets

```bash
cp .env.aws.example .env
nano .env   # DOMAIN/WWW_DOMAIN/BRIEFS_DOMAIN, POSTGRES_PASSWORD, API_AUTH_KEY, LLM keys, etc.
```

### 6. Bring up Postgres and migrate data from your local instance

Postgres first, alone, so data can be restored into a clean database before the
backend's own startup migrations touch it — skip this if starting empty:

```bash
docker compose -f docker-compose.yml -f docker-compose.aws.yml up -d postgres
```

From your local machine, where the local `docker-compose` Postgres already has real
data:

```powershell
docker exec news-summarizer-new-db pg_dump -U news_user -d news_summarizer -F c -f /tmp/local_dump.sql
docker cp news-summarizer-new-db:/tmp/local_dump.sql .\local_dump.sql
scp -i path\to\key.pem .\local_dump.sql ubuntu@<ELASTIC_IP>:/home/ubuntu/
```

Back on the instance:

```bash
docker cp /home/ubuntu/local_dump.sql news-summarizer-new-db:/tmp/local_dump.sql
docker exec news-summarizer-new-db pg_restore -U news_user -d news_summarizer --clean --if-exists /tmp/local_dump.sql
```

### 7. Bring up the app and verify internally, before touching DNS

Start backend, frontend, and cron — **not Caddy yet**:

```bash
docker compose -f docker-compose.yml -f docker-compose.aws.yml up -d --build backend frontend cron-job
curl localhost:8000/health
curl -I localhost:5173
```

Fix anything that doesn't come back clean here first. This matters because Caddy
requests its Let's Encrypt certificate the moment DNS resolves and it gets a real
request — repeated failed attempts against a broken backend can hit Let's Encrypt's
retry rate limit (a handful of failures per hostname per hour) and lock you out of
retrying for a while.

### 8. DNS

In wherever `ecobriefbolivia.online`'s DNS is managed (Hostinger's DNS panel, even
though the server itself is down — the DNS zone is usually independent), point all
three hostnames at the Elastic IP:

```text
ecobriefbolivia.online          A   <ELASTIC_IP>
www.ecobriefbolivia.online      A   <ELASTIC_IP>
briefs.ecobriefbolivia.online   A   <ELASTIC_IP>
```

Wait for propagation (`dig ecobriefbolivia.online` from your machine should return
the Elastic IP) before the next step.

### 9. Start Caddy

```bash
docker compose -f docker-compose.yml -f docker-compose.aws.yml up -d --build caddy
docker compose -f docker-compose.yml -f docker-compose.aws.yml logs -f caddy
```

Watch the logs for the certificate to come through clean for all three hostnames.

### 10. Guard against surprise charges

AWS Budgets -> create a **zero-spend budget** (or a $1 threshold budget with an email
alert). With everything above inside the free tier this should never fire, but it's a
free safety net worth the two minutes it takes to set up.

### 11. Verify

```bash
curl -I https://ecobriefbolivia.online/health
curl -I https://www.ecobriefbolivia.online/health
curl -I https://briefs.ecobriefbolivia.online/health
```

Check `/api/news`, `/api/economic-indicators`, and the subscribe flow from a browser.
Since Hostinger is down there's no shared-webhook conflict to worry about — once this
looks good, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_WEBHOOK_URL` and the WhatsApp credentials
can point at this deployment directly.

### 12. Continuous deployment

`.github/workflows/deploy-aws.yml` runs after the existing `CI` workflow succeeds on
`main`: it builds the backend/frontend/cron images, pushes them to GitHub Container
Registry (`ghcr.io/jhoshoa/news-summarizer-{backend,frontend,cron}`), then SSHes into
the instance to `git pull`, `docker compose pull`, and `docker compose up -d` — the
build itself never runs on the instance again after the manual first deploy above.

Both the push (build job) and the pull (deploy job, over the SSH connection) authenticate
to GHCR with `secrets.GITHUB_TOKEN` — the token GitHub Actions generates automatically
for every run, scoped only to this repository and expired the moment the run ends.
Nothing to create for that part.

Add these two repo secrets (Settings -> Secrets and variables -> Actions -> New
repository secret) so the workflow can reach the instance:

- **`EC2_HOST`** — the Elastic IP from step 3.
- **`EC2_SSH_KEY`** — the full contents of the `.pem` key pair from step 2. Anyone with
  this secret can SSH into the instance as `ubuntu`; treat it like a production
  credential.

The workflow assumes `~/news-summarizer` on the instance is the same git checkout used
in step 4 and that `.env` (step 5) is already in place — it only pulls code and images,
it never touches secrets on the server.

## Distribution Channels (Email / WhatsApp / Telegram)

Each channel degrades independently: if it's not configured, `/api/preferences/options`
reports it as unavailable in the subscribe form and sends silently fail (logged, not
raised) rather than breaking delivery for other channels.

**Email** — set `EMAIL_ENABLED=true` and `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM_EMAIL`.
With Gmail, use an App Password, not the account password, and rotate it if it was ever
committed or shared. Gmail can rate-limit or spam-flag bulk sends without SPF/DKIM on a
custom domain — consider a transactional provider (SES, Postmark, Resend) before scaling
past a handful of daily subscribers.

**WhatsApp** — the app talks directly to the Meta WhatsApp Cloud API (no Twilio or other
BSP in between; Twilio required mandatory auto-recharge or suspended the account, plus its
own markup on top of Meta's rate). Set `WHATSAPP_META_ACCESS_TOKEN` and
`WHATSAPP_META_PHONE_NUMBER_ID` from your Meta app's WhatsApp product. In dev mode you're
limited to 5 test numbers; for real subscribers you need a Meta-approved WhatsApp Business
sender, which requires business verification and approved message templates for anything
sent outside a 24h user-initiated window. There is no "send to a WhatsApp group" API on the
WhatsApp Business Platform — only one-to-one messages to opted-in numbers (a broadcast
list, not a group).

Also set `WHATSAPP_META_VERIFY_TOKEN` (a string you choose, used for Meta's webhook
subscription handshake) and `WHATSAPP_META_APP_SECRET` (from the Meta app's Basic
Settings). The app uses the app secret to validate the `X-Hub-Signature-256` header on
every incoming request — without it, anyone who finds the URL could POST fake messages
(e.g. unsubscribe any phone number by faking "cancelar"). If `WHATSAPP_META_APP_SECRET` is
left empty the endpoint still works but skips signature validation entirely, so set it
before pointing real traffic at the webhook.

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
