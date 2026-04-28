# ShopSerp

Self-hosted Google Shopping search, price monitoring, store reputation, and price analytics service.

ShopSerp provides a FastAPI backend, a lightweight browser UI, an authenticated external API, scheduled product monitors, alert webhooks, and a curated reputable-store registry across multiple countries. It is designed to be self-hosted and integrated with inventory/commerce systems that need product price intelligence without depending on a single marketplace.

## Table of Contents

- [What ShopSerp Does](#what-shopserp-does)
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Runtime Stack](#runtime-stack)
- [Search Backends](#search-backends)
- [Supported Countries](#supported-countries)
- [Quick Start with Docker](#quick-start-with-docker)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Database Model](#database-model)
- [API Overview](#api-overview)
- [External API Authentication](#external-api-authentication)
- [Examples](#examples)
- [Frontend UI](#frontend-ui)
- [Scheduler and Monitoring](#scheduler-and-monitoring)
- [Alerts](#alerts)
- [Custom Stores](#custom-stores)
- [Testing and Quality Checks](#testing-and-quality-checks)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)
- [Development Notes](#development-notes)

## What ShopSerp Does

ShopSerp searches Google Shopping or search-provider APIs for product listings, normalizes results, tags sellers against a reputable-store registry, stores monitor history, and exposes analytics for downstream systems.

Typical use cases:

- Find current retail pricing for a UPC, part number, SKU, brand/model, or free-text product query.
- Compare prices across countries and currencies.
- Track a product over time and retain historical price records.
- Alert when a product drops below a threshold or changes price materially.
- Validate whether a seller/domain is known and reputable.
- Integrate pricing intelligence into systems such as inventory, refurbishment, quoting, or marketplace tools.

## Core Features

- **Multi-country product search** with country-specific Google parameters, currencies, and store registries.
- **Multiple search backends**:
  - Serper.dev API when `SERPER_API_KEY` is set.
  - SerpAPI when `SERPAPI_KEY` is set.
  - Playwright Chromium scraping as a no-key fallback.
- **Structured search** for integrations using UPC, manufacturer part number, SKU, brand, model, condition, and free-text fallback.
- **Product monitors** that periodically scrape and store prices.
- **Historical analytics** including current stats, reputable-only stats, price history, store breakdown, and distribution buckets.
- **Alerting** for below-threshold, price-drop, and back-in-stock events with optional webhook delivery.
- **Reputable-store registry** with 17 supported countries and 500+ known store domains.
- **Custom stores** stored in SQLite and loaded into the in-memory registry on startup.
- **API key management** for external integrations.
- **Static frontend UI** served by the same FastAPI app.
- **Docker-first deployment** with persistent SQLite volume.

## Architecture

```text
Browser UI / External Systems
          |
          v
    FastAPI application
          |
          +-- UI/API routers
          |     - search
          |     - monitors
          |     - analytics
          |     - settings/countries
          |     - API keys
          |     - external /api/v1
          |
          +-- Services
          |     - SearchService
          |     - MonitorService
          |     - AnalyticsService
          |     - AlertService
          |     - Custom store service
          |
          +-- Search backends
          |     - Serper.dev API
          |     - SerpAPI
          |     - Playwright Google Shopping scraper
          |
          +-- Store registry
          |     - Built-in reputable stores
          |     - DB-backed custom stores
          |
          +-- SQLite via async SQLAlchemy
          |
          +-- APScheduler background monitor runner
```

The application starts in `backend/main.py`. Startup initializes the database tables, loads custom stores into the registry, starts the scheduler, registers API routers, and serves the static frontend.

## Repository Layout

```text
.
├── backend/
│   ├── main.py                     # FastAPI app entry point and lifecycle
│   ├── config.py                   # Pydantic settings from env/.env
│   ├── database.py                 # Async SQLAlchemy engine/session/init
│   ├── models.py                   # ORM models
│   ├── schemas.py                  # Pydantic request/response schemas
│   ├── auth.py                     # X-API-Key auth for external API
│   ├── scheduler.py                # APScheduler monitor runner
│   ├── routers/
│   │   ├── search.py               # Internal/UI search endpoints
│   │   ├── monitors.py             # Internal/UI monitor and alert endpoints
│   │   ├── analytics.py            # Internal/UI analytics endpoints
│   │   ├── settings_router.py      # Countries, store listings, health
│   │   ├── api_keys.py             # API key CRUD
│   │   └── external.py             # Authenticated /api/v1 integration API
│   ├── services/
│   │   ├── search.py               # Search orchestration and filtering
│   │   ├── monitor.py              # Monitor CRUD/check persistence
│   │   ├── analytics.py            # Aggregations and history
│   │   ├── alerts.py               # Alert evaluation and webhook dispatch
│   │   └── custom_stores.py        # Custom store persistence/registry sync
│   ├── scraper/
│   │   ├── google_shopping.py      # Playwright scraper
│   │   ├── serper_api.py           # Serper.dev backend
│   │   ├── parser.py               # Google Shopping HTML parsers
│   │   ├── proxy.py                # Proxy pool helper
│   │   └── user_agents.py          # User-agent rotation
│   └── stores/
│       └── registry.py             # Reputable store/country registry
├── frontend/
│   ├── index.html                  # Static single-page UI
│   ├── app.js                      # UI routing/state/API logic
│   └── style.css                   # UI styling
├── tests/
│   ├── conftest.py                 # Async test app/database fixtures
│   ├── test_api.py                 # API integration tests
│   └── test_stores.py              # Store registry tests
├── Dockerfile                      # Playwright Python runtime image
├── docker-compose.yml              # Single-service deployment
├── requirements.txt                # Runtime Python dependencies
├── pyproject.toml                  # Project metadata, pytest, ruff config
└── .env.example                    # Configuration template
```

## Runtime Stack

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy async ORM
- SQLite with `aiosqlite` by default
- Pydantic Settings
- HTTPX
- BeautifulSoup/lxml
- Playwright Chromium
- APScheduler
- Static HTML/CSS/JavaScript frontend
- Docker image based on `mcr.microsoft.com/playwright/python:v1.52.0-noble`

## Search Backends

ShopSerp chooses the search backend at process startup in this priority order:

1. **Serper.dev** if `SERPER_API_KEY` is configured.
2. **SerpAPI** if `SERPAPI_KEY` is configured.
3. **Playwright Google Shopping scraper** if no API key is configured.

### Serper.dev

Recommended for reliable production search. It returns structured Shopping JSON and avoids browser scraping issues.

Set:

```env
SERPER_API_KEY=your-serper-key
```

### SerpAPI

Alternative paid/free-tier Google Shopping API.

Set:

```env
SERPAPI_KEY=your-serpapi-key
```

### Playwright Fallback

No API key is required, but direct scraping may encounter CAPTCHA/rate limiting from datacenter IPs. For best results, deploy behind a reliable residential proxy.

Set:

```env
PROXY_URL=http://user:password@proxy-host:port
PROXY_ROTATION_ENABLED=true
```

> Note: the current Playwright scraper code includes proxy helper support in the repository, but proxy behavior should be verified in your deployment before relying on it for production scraping.

## Supported Countries

The built-in registry currently supports 17 countries:

| Code | Country | Currency | Built-in stores |
|---|---|---:|---:|
| US | United States | USD | 33 |
| AU | Australia | AUD | 26 |
| GB | United Kingdom | GBP | 27 |
| DE | Germany | EUR | 20 |
| JP | Japan | JPY | 17 |
| CA | Canada | CAD | 15 |
| FR | France | EUR | 15 |
| IN | India | INR | 13 |
| NZ | New Zealand | NZD | 12 |
| SG | Singapore | SGD | 9 |
| KR | South Korea | KRW | 11 |
| BR | Brazil | BRL | 11 |
| IT | Italy | EUR | 8 |
| ES | Spain | EUR | 8 |
| NL | Netherlands | EUR | 8 |
| SE | Sweden | SEK | 9 |
| MX | Mexico | MXN | 11 |

The store registry contains more than 500 reputable domains across these countries.

## Quick Start with Docker

### 1. Clone the repository

```bash
git clone https://github.com/navidrast/shopserp.git
cd shopserp
```

### 2. Create configuration

```bash
cp .env.example .env
```

Edit `.env` and set at least a database URL and, for reliable search, one search API key:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/shopserp.db
DEFAULT_COUNTRIES=US,AU
SERPER_API_KEY=your-serper-key
```

### 3. Start the service

```bash
docker compose up -d --build
```

### 4. Check health

```bash
curl http://localhost:8888/health
```

Expected response:

```json
{"status":"ok","version":"0.1.0"}
```

### 5. Open the UI

Visit:

```text
http://localhost:8888
```

The Compose file maps host port `8888` to container port `8000`.

## Local Development

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff mypy
```

### 3. Install Playwright browser assets

If you run without Docker and use the Playwright fallback:

```bash
playwright install chromium
```

### 4. Configure environment

```bash
cp .env.example .env
```

For local development:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/shopserp.db
SERPER_API_KEY=your-serper-key
LOG_LEVEL=DEBUG
```

### 5. Run the app

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

```text
http://localhost:8000
```

API docs are available at:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

## Configuration

All settings are loaded from environment variables or `.env` via `backend/config.py`.

| Variable | Default | Description |
|---|---:|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./shopserp.db` | Async SQLAlchemy database URL. Compose uses `./data/shopserp.db`. |
| `SCRAPE_INTERVAL_MINUTES` | `360` | Default monitor interval in minutes. |
| `DEFAULT_COUNTRIES` | `US` | Comma-separated countries used when a request provides none. |
| `PROXY_URL` | empty | One or more proxy URLs. Comma-separated values are supported by the proxy helper. |
| `PROXY_ROTATION_ENABLED` | `false` | Indicates whether proxy rotation should be enabled. |
| `REQUEST_TIMEOUT` | `30` | Outbound scrape/search timeout in seconds. |
| `MAX_CONCURRENT_SCRAPES` | `3` | Max concurrent country searches/scrapes. |
| `ALERT_WEBHOOK_URL` | empty | Optional webhook called when alerts fire. |
| `LOG_LEVEL` | `INFO` | Python logging level. |
| `SERPER_API_KEY` | empty | Serper.dev API key. Preferred production search backend. |
| `SERPAPI_KEY` | empty | SerpAPI key. Used when Serper is not configured. |
| `SECRET_KEY` | empty | Reserved for auth/session needs. |
| `API_KEYS` | empty | Comma-separated `name:key` pairs for `/api/v1` auth. |

Example `.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/shopserp.db
SCRAPE_INTERVAL_MINUTES=360
DEFAULT_COUNTRIES=US,AU,GB
REQUEST_TIMEOUT=30
MAX_CONCURRENT_SCRAPES=3
LOG_LEVEL=INFO
SERPER_API_KEY=your-serper-key
ALERT_WEBHOOK_URL=https://example.com/webhook
API_KEYS=returnpilot:sk-change-me
```

## Database Model

ShopSerp creates tables automatically at startup using SQLAlchemy metadata. There is no Alembic migration system in the current codebase.

Main models:

### `products`

A product/search target.

Important fields:

- `id`
- `name`
- `query`
- `is_active`
- `created_at`
- `updated_at`

### `monitors`

A country-specific monitor for a product.

Important fields:

- `id`
- `product_id`
- `country_code`
- `enabled`
- `interval_minutes`
- `last_checked`

### `price_records`

A normalized search result captured during a monitor check.

Important fields:

- `monitor_id`
- `store_name`
- `store_domain`
- `price`
- `currency`
- `original_price`
- `url`
- `title`
- `condition`
- `shipping`
- `in_stock`
- `is_reputable`
- `scraped_at`

### `price_alerts`

Alert rules attached to monitors.

Supported `alert_type` values:

- `below_threshold`
- `price_drop`
- `back_in_stock`

### `api_keys`

DB-managed external API keys. Raw keys are only returned once; SHA-256 hashes are stored.

### `custom_stores`

User-defined stores that are loaded into the in-memory reputable-store registry on startup.

## API Overview

ShopSerp exposes two API groups:

1. `/api/*` — used by the built-in UI and internal workflows.
2. `/api/v1/*` — external integration API protected by `X-API-Key` when keys are configured.

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Container-friendly health endpoint. |
| `GET` | `/api/health` | API health endpoint. |
| `GET` | `/api/v1` routes use `/api/v1/...` | External routes described below. |

### Internal/UI API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/search` | Search Google Shopping across countries. |
| `GET` | `/api/countries` | List supported countries. |
| `GET` | `/api/countries/{code}/stores` | List reputable stores for a country. |
| `GET` | `/api/monitors` | List products and monitors. |
| `POST` | `/api/monitors` | Create a monitored product. |
| `GET` | `/api/monitors/{product_id}` | Product monitor detail. |
| `DELETE` | `/api/monitors/{product_id}` | Delete a product and associated monitor data. |
| `PATCH` | `/api/monitors/{monitor_id}/toggle` | Enable or disable a monitor. |
| `POST` | `/api/monitors/{product_id}/countries` | Add a country monitor to a product. |
| `DELETE` | `/api/monitors/{product_id}/countries/{country_code}` | Remove a country monitor. |
| `POST` | `/api/monitors/{monitor_id}/check` | Run an immediate monitor check. |
| `POST` | `/api/monitors/{monitor_id}/alerts` | Create an alert. |
| `GET` | `/api/monitors/{monitor_id}/alerts` | List alerts for a monitor. |
| `DELETE` | `/api/monitors/alerts/{alert_id}` | Delete an alert. |
| `GET` | `/api/analytics/{monitor_id}` | Price analytics for one monitor. |
| `GET` | `/api/analytics/{product_id}/history` | Product price history by country. |
| `GET` | `/api/analytics/{monitor_id}/compare` | Latest store comparison. |
| `POST` | `/api/keys` | Create an external API key. |
| `GET` | `/api/keys` | List API key metadata. |
| `PATCH` | `/api/keys/{key_id}` | Toggle an API key active/inactive. |
| `DELETE` | `/api/keys/{key_id}` | Delete/revoke an API key. |

### External `/api/v1` API

All `/api/v1` routes use the `require_api_key` dependency.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/search` | Structured or free-text search. |
| `GET` | `/api/v1/stores/check` | Check store reputation by domain or name. |
| `GET` | `/api/v1/stores/{country_code}` | List reputable stores for a country. |
| `POST` | `/api/v1/stores/custom` | Create a custom reputable store. |
| `GET` | `/api/v1/stores/custom` | List custom stores. |
| `DELETE` | `/api/v1/stores/custom/{store_id}` | Delete a custom store. |
| `POST` | `/api/v1/monitors` | Create a monitored product. |
| `GET` | `/api/v1/monitors` | List monitored products. |
| `GET` | `/api/v1/monitors/{product_id}` | Get monitor detail. |
| `DELETE` | `/api/v1/monitors/{product_id}` | Delete a monitored product. |
| `POST` | `/api/v1/monitors/{monitor_id}/check` | Trigger a monitor check. |
| `GET` | `/api/v1/analytics/{monitor_id}` | Monitor analytics. |
| `GET` | `/api/v1/analytics/{product_id}/history` | Product history. |
| `GET` | `/api/v1/analytics/{monitor_id}/compare` | Store comparison. |
| `GET` | `/api/v1/countries` | List supported countries. |

## External API Authentication

External API auth checks `X-API-Key` against two sources:

1. `API_KEYS` environment variable, using comma-separated `name:key` pairs.
2. The `api_keys` database table, using SHA-256 hashes.

Example:

```env
API_KEYS=returnpilot:sk-returnpilot-secret,partner:sk-partner-secret
```

Request:

```bash
curl -X POST http://localhost:8888/api/v1/search \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: sk-returnpilot-secret' \
  -d '{"query":"iPhone 15 Pro 256GB","countries":["US","AU"],"max_results":10}'
```

Important behavior: if no API keys exist in either `API_KEYS` or the database, `/api/v1` authentication is disabled and requests are treated as `anonymous`.

## Examples

### Search from the internal API

```bash
curl -X POST http://localhost:8888/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Sony WH-1000XM5",
    "countries": ["US", "AU"],
    "max_results": 20
  }'
```

### Structured external search

```bash
curl -X POST http://localhost:8888/api/v1/search \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: sk-returnpilot-secret' \
  -d '{
    "upc": "195949019774",
    "brand": "Apple",
    "model": "iPhone 15 Pro",
    "condition": "new",
    "countries": ["US"],
    "max_results": 10
  }'
```

Search fallback order for structured requests:

1. UPC/EAN
2. Part number, optionally prefixed with brand
3. Brand + model
4. Free-text query

### Check store reputation

```bash
curl 'http://localhost:8888/api/v1/stores/check?domain=bestbuy.com&country_code=US' \
  -H 'X-API-Key: sk-returnpilot-secret'
```

### Create a monitor

```bash
curl -X POST http://localhost:8888/api/monitors \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "iPhone 15 Pro 256GB",
    "query": "iPhone 15 Pro 256GB unlocked",
    "countries": ["US", "AU"],
    "interval_minutes": 360
  }'
```

### Trigger a monitor check

```bash
curl -X POST http://localhost:8888/api/monitors/1/check
```

### Fetch analytics

```bash
curl 'http://localhost:8888/api/analytics/1?days=30'
```

### Create an alert

```bash
curl -X POST http://localhost:8888/api/monitors/1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "alert_type": "below_threshold",
    "threshold_value": 499.99
  }'
```

### Create an API key through the UI/internal endpoint

```bash
curl -X POST http://localhost:8888/api/keys \
  -H 'Content-Type: application/json' \
  -d '{"name":"returnpilot"}'
```

The raw key is returned once. Store it securely.

## Frontend UI

The frontend is a lightweight static single-page app located in `frontend/` and served directly by FastAPI.

It provides:

- Search page
- Monitor list/detail views
- Product pricing views
- Settings/country management screens
- API key management
- Dark/light theme support

The frontend calls the internal `/api/*` endpoints and does not require a separate build step.

## Scheduler and Monitoring

`backend/scheduler.py` starts an APScheduler `AsyncIOScheduler` on application startup.

Current behavior:

- Scheduler wakes every 10 minutes.
- It loads enabled monitors.
- A monitor is due if `last_checked` is missing or older than `interval_minutes`.
- Due monitor checks run concurrently up to `MAX_CONCURRENT_SCRAPES`.
- Each monitor check stores price records, updates `last_checked`, and evaluates alerts.

Monitor checks can also be triggered manually through:

```text
POST /api/monitors/{monitor_id}/check
POST /api/v1/monitors/{monitor_id}/check
```

## Alerts

Supported alert types:

### `below_threshold`

Triggers when any latest price is below `threshold_value`.

### `price_drop`

Triggers when the average price drops by more than the configured internal threshold, currently 10%, compared with previous data.

### `back_in_stock`

Intended for stock reappearance detection when a previously unavailable item returns.

When `ALERT_WEBHOOK_URL` is set, alert payloads are sent to that webhook on a best-effort basis.

## Custom Stores

Custom stores allow you to extend the reputable-store registry without changing code.

Create one via `/api/v1/stores/custom`:

```bash
curl -X POST http://localhost:8888/api/v1/stores/custom \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: sk-returnpilot-secret' \
  -d '{
    "name": "Example Electronics",
    "domain": "example-electronics.com",
    "aliases": ["Example Store"],
    "category": "electronics",
    "tier": 2,
    "country_codes": ["US", "AU"]
  }'
```

Custom stores are persisted in SQLite and loaded into the in-memory registry during startup.

## Testing and Quality Checks

### Run tests

```bash
python -m pytest tests/ -v
```

The test suite uses an in-memory SQLite database and FastAPI ASGI transport.

### Run lint

```bash
ruff check backend/
```

### Run format check

```bash
ruff format --check backend/
```

### Run the same core checks as CI

```bash
pip install -r requirements.txt pytest pytest-asyncio httpx ruff mypy
ruff check backend/
ruff format --check backend/
python -m pytest tests/ -v --tb=short
```

## Deployment

### Docker Compose

`docker-compose.yml` runs a single service:

- Container name: `shopserp`
- Host port: `8888`
- App port: `8000`
- Persistent volume: `./data:/app/data`
- Environment file: `.env`
- Restart policy: `unless-stopped`
- Memory limit: `1024M`

Start:

```bash
docker compose up -d --build
```

Logs:

```bash
docker compose logs -f shopserp
```

Stop:

```bash
docker compose down
```

### GitHub Actions

The repository includes:

- `.github/workflows/ci.yml`
  - Ruff lint
  - Ruff format check
  - Pytest
  - Docker build and container health check
- `.github/workflows/release.yml`
  - Builds and publishes Docker image to GHCR on `v*` tags

## Security Notes

Review these before exposing ShopSerp publicly.

1. **Internal `/api/*` endpoints are not authenticated by the application.**
   - The code comments indicate the UI may be protected by a network layer such as Cloudflare Access.
   - If exposed to the internet, protect the whole app with a reverse proxy, identity-aware proxy, VPN, or application auth.

2. **External `/api/v1/*` auth is disabled if no keys are configured.**
   - Set `API_KEYS` or create at least one DB API key before exposing the external API.

3. **CORS is currently permissive.**
   - `backend/main.py` allows all origins, methods, and headers.
   - Restrict this in production if browsers will call the API directly.

4. **API key management endpoints are not individually authenticated.**
   - Protect `/api/keys` behind your network/auth layer.

5. **SQLite is simple and appropriate for small self-hosted deployments.**
   - For high write volume, multi-instance deployments, or HA needs, migrate to PostgreSQL and add explicit migrations.

6. **Scraping Google directly can violate rate limits and trigger CAPTCHA.**
   - Prefer a search API provider or a compliant proxy strategy.

7. **Do not commit `.env` or secrets.**
   - `.gitignore` excludes environment files; keep it that way.

## Troubleshooting

### Health check fails in Docker

Check logs:

```bash
docker compose logs -f shopserp
```

Common causes:

- Invalid `.env` syntax.
- Database path not writable.
- Port `8888` already in use.

### Search returns no results

Check:

- `SERPER_API_KEY` or `SERPAPI_KEY` is valid.
- Country codes are uppercase ISO codes like `US`, `AU`, `GB`.
- `max_results` is between 1 and 100.
- Logs for provider errors or CAPTCHA messages.

### Playwright receives CAPTCHA

Use Serper.dev/SerpAPI for production, or configure a suitable proxy.

### API returns 401

For `/api/v1`:

- Include `X-API-Key`.
- Ensure the key exists in `API_KEYS` or was created through `/api/keys`.
- Ensure DB-created keys have not been toggled inactive or deleted.

### Data disappears between container restarts

Ensure `./data` is mounted and `DATABASE_URL` points inside `/app/data` when using Docker:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/shopserp.db
```

## Development Notes

- The app initializes tables automatically with `Base.metadata.create_all`; there are no migrations currently.
- Search backend selection happens when `SearchService` is constructed, so changing `SERPER_API_KEY`/`SERPAPI_KEY` requires an app restart.
- Custom stores are loaded into the registry at startup. Creating/deleting stores also updates the in-memory registry immediately in the running process.
- The static frontend is intentionally framework-free and served from `frontend/`.
- The external v1 API is the safer integration surface for downstream systems because it centralizes API key auth.

## License

No license file is currently present in this repository. Add one before publishing or distributing the project outside your organization.
