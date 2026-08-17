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

The cron container uses Docker's internal network:

```env
BACKEND_BASE_URL=http://backend:8000
```

That value is defined directly in `docker-compose.yml` because the backend and cron services run in the same Compose project.

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
