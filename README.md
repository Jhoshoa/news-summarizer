# News Summarizer Bolivia

FastAPI service that collects Bolivian news, summarizes it with an LLM, and can distribute summaries through WhatsApp or Telegram.

## Current Behavior

- Collects news from Bolivian sites listed in `config/sources.yaml`.
- Uses `httpx + BeautifulSoup + lxml` for scraping. Playwright is not required for the current scraper.
- Uses NewsAPI as an additional source. Because NewsAPI does not reliably support Bolivia through `top-headlines`, the app falls back to `/v2/everything` searches for Bolivia-related articles.
- Deduplicates, classifies, ranks, summarizes, and optionally rewrites news before delivery.
- Runs without PostgreSQL. Database failures are logged and the API continues.
- Requires PostgreSQL only for subscribers, saved preferences, `/stats`, and message delivery.

## Requirements

- Python 3.11+
- Groq or OpenAI API key for summaries
- NewsAPI key if you want the NewsAPI collector enabled
- PostgreSQL only when you want subscriptions and delivery
- Redis is configured but not required for the current manual summary flow

## Setup

Create and activate the virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

Install development tools only when you want linting, typing, or tests:

```powershell
pip install -r requirements-dev.txt
```

Copy the environment file:

```powershell
copy .env.example .env
```

Then edit `.env` with your keys:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here

NEWS_API_KEY=your_newsapi_key
NEWS_API_COUNTRY=bo
NEWS_API_LANGUAGE=es

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/news_summarizer
```

## Running Locally

Run the API:

```powershell
uvicorn src.main:app --reload
```

Or:

```powershell
python -m src.main
```

The API runs at:

```text
http://localhost:8000
```

## Useful Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | App status |
| GET | `/health` | Health check |
| GET | `/stats` | Subscriber count; returns `0` when DB is unavailable |
| POST | `/trigger/summary` | Collect, process, summarize, and deliver when subscribers exist |
| POST | `/webhook/whatsapp` | Twilio WhatsApp webhook |

Manual summary trigger:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/trigger/summary?time_of_day=manual" -Method Post -UseBasicParsing
```

Expected result without PostgreSQL:

```json
{
  "status": "success",
  "message": "Resumen manual procesado",
  "result": {
    "collected": 20,
    "summaries": 11,
    "sent": 0
  }
}
```

The exact counts depend on source availability and LLM output.

## Collectors

### Web Scraper

The scraper reads enabled sources from `config/sources.yaml`.

Each source can define:

```yaml
sources:
  - name: "RadioFides"
    url: "https://www.radiofides.com/"
    category: "general"
    selector: "article.post, article"
    title_selector: "h2 a, h3 a"
    url_selector: "a.post-link, a"
    date_selector: ".post-date, .date, time"
    image_selector: "img"
    enabled: true
```

If a source layout changes and the configured selectors find no articles, the scraper now uses a generic article-link fallback. This is why the app can still collect from sources whose homepage HTML does not match the original selectors exactly.

### NewsAPI

For countries supported by NewsAPI `top-headlines`, the collector uses that endpoint.

For `NEWS_API_COUNTRY=bo`, it uses `/v2/everything` with Bolivia-focused queries such as:

- `Bolivia AND (politica OR gobierno OR elecciones OR presidente)`
- `Bolivia AND (economia OR dolar OR banco OR finanzas)`
- `Bolivia AND (deportes OR futbol OR liga OR seleccion)`

The collector also filters returned articles so Bolivia is mentioned in the title, description, or content.

## Processing Pipeline

`/trigger/summary` runs this flow:

1. Scrape configured sources when `SCRAPER_ENABLED=true`.
2. Fetch NewsAPI articles when `NEWS_API_KEY` is configured.
3. Deduplicate by URL and similar titles.
4. Classify into configured categories.
5. Rank articles by recency, source trust, and category quality.
6. Summarize with Groq or OpenAI.
7. Rewrite summaries for consistent style.
8. Deliver to active subscribers if PostgreSQL is available.

If the DB is not available, the endpoint still returns collection and summary counts, with `sent: 0`.

## Validation Commands

Runtime import check:

```powershell
python -c "from src.main import app; print(app.title)"
```

Lint check, if dev dependencies are installed:

```powershell
python -m ruff check src tests
```

Tests, if test files exist:

```powershell
python -m pytest
```

At the moment, the repository has no test files, so `pytest` may report `collected 0 items`.

## PostgreSQL

PostgreSQL is optional for local collector and LLM testing.

Start it when you want subscribers, preferences, and delivery:

```powershell
docker-compose up -d
```

Without PostgreSQL:

- API startup still works.
- `/health` works.
- `/trigger/summary` can collect and summarize.
- `/stats` returns `0`.
- Delivery is skipped.

## Project Structure

```text
news-summarizer/
  config/
    sources.yaml          News source definitions
  src/
    collectors/           NewsAPI and web scraper collectors
    config/               Settings and environment loading
    db/                   SQLAlchemy subscriber repository
    distributors/         WhatsApp and Telegram handlers
    llm/                  Groq/OpenAI-compatible client
    processors/           Deduplication, classification, ranking, summaries
    scheduler/            Scheduled jobs
    main.py               FastAPI entry point
  tests/
  requirements.txt        Runtime dependencies
  requirements-dev.txt    Optional development dependencies
```

## Troubleshooting

### The API starts but `/stats` returns zero

PostgreSQL is not running or no subscribers exist. This is expected during local collector testing.

### The scraper returns no articles

- Check that the site is reachable from your network.
- Check `config/sources.yaml`.
- Look for scraper logs showing whether selector extraction or fallback extraction ran.

### NewsAPI returns unrelated articles

NewsAPI is broader than the local scrapers. The collector now filters Bolivia mentions, but some results can still be less relevant than direct Bolivian sources.

### Groq errors

Check:

- `LLM_PROVIDER=groq`
- `GROQ_API_KEY=gsk_...`
- The Groq free-tier rate limit has not been reached.

## Notes

- Playwright is no longer part of the current runtime setup.
- `requirements-dev.txt` is optional and exists for linting, typing, tests, and local development checks.
- Do not commit real `.env` secrets.
