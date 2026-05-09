# Repository Guidelines

## Project Structure & Module Organization

This Python 3.11+ FastAPI service collects, summarizes, and distributes Bolivian news. Application code lives in `src/`, with `src/main.py` as the API entry point. Major modules are grouped by responsibility: `collectors/` fetch news, `processors/` deduplicate/classify/rank/summarize/rewrite articles, `llm/` wraps AI providers, `distributors/` handles WhatsApp and Telegram, `db/` manages persistence, `scheduler/` runs scheduled jobs, and `config/` loads settings. Scraper source definitions live in `config/sources.yaml`; design notes and diagrams are under `docs/`; tests belong in `tests/`.

## Build, Test, and Development Commands

- `python -m venv venv` then `venv\Scripts\activate`: create and activate a Windows virtual environment.
- `pip install -r requirements.txt`: install runtime dependencies.
- `pip install -r requirements-dev.txt`: install test, lint, and typing tools.
- `playwright install chromium`: install the browser for scraping workflows.
- `python -m src.main`: run the FastAPI app locally.
- `uvicorn src.main:app --reload`: run with reload at `http://localhost:8000`.
- `docker-compose up -d`: start Postgres.
- `pytest`: run the test suite.
- `ruff check src tests`: lint source and tests.
- `mypy src`: run static type checks.

## Coding Style & Naming Conventions

Use 4-space indentation and keep code compatible with Python 3.11. Follow the existing package layout and prefer small modules grouped by responsibility. Use `snake_case` for functions, methods, variables, and module filenames; use `PascalCase` for classes. Ruff enforces a 100-character line length plus import sorting, naming, bugbear, comprehension, and simplification checks.

## Testing Guidelines

Pytest is configured in `pyproject.toml` with `tests/` as the test root. Name files `test_*.py` and functions `test_*`. Use `pytest-asyncio` for async collectors, API flows, and distributor interactions. Mock Groq/OpenAI, NewsAPI, Twilio, Telegram, and live news sites. Coverage is scoped to `src/`; add focused tests when changing processors, settings, database behavior, or webhooks.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so no local convention can be inferred. Use short, imperative subjects such as `Add scraper timeout setting` or `Fix Telegram preference flow`. Pull requests should include a description, test results (`pytest`, `ruff`, `mypy` when relevant), linked issues, and screenshots or sample API responses for visible endpoint changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` for local configuration, but never commit real secrets. Keep provider keys, Twilio credentials, Telegram tokens, and database URLs in environment variables. When adding sources, update `config/sources.yaml` and validate selectors without committing logs, cache files, virtual environments, or Playwright artifacts.
