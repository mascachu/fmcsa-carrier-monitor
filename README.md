# FMCSA Daily Change Monitor — Portfolio Prototype

A portfolio prototype for monitoring FMCSA carrier insurance and authority changes, recording change history, and preparing alerts.

## Features

- FastAPI service with PostgreSQL storage
- FMCSA daily-difference dataset configuration
- Carrier watchlist matching by USDOT and MC identifiers
- Change-event history with duplicate prevention
- Run-history tracking and API endpoints
- Docker Compose development environment
- n8n workflow demo scaffold
- Optional Zoho CRM integration, disabled by default

## Verified checks

- Docker API container starts successfully.
- PostgreSQL container reports healthy status.
- `GET /health` returns HTTP 200 with service status `ok`.
- `GET /sources` returns the configured FMCSA daily-difference dataset identifiers.
- Synthetic demo records match the configured test watchlist.
- The first synthetic demo run creates two change events.
- Re-running the same demo creates zero additional duplicate events.
- `GET /events` returns the two stored demo events.
- A synthetic run-history record can be retrieved through `GET /runs`.
- Automated test suite: **15 passed** in the Docker container.
- Zoho synchronization and task creation remain disabled during the demo.

## Run the synthetic demo

Ensure Docker Compose services are running, then execute from the project root:

```bash
docker compose up -d --build
docker compose exec api python -m scripts.run_demo
```

The demo uses synthetic carrier records from `data/sample/demo_carrier_rows.json` and the test watchlist in `data/sample/demo_watchlist.csv`.

Import the demo watchlist into the Docker database before running the demo if it has not already been imported:

```bash
docker compose exec -T api python -c "import csv; from app.repository import import_watchlist; rows=list(csv.DictReader(open('/app/data/sample/demo_watchlist.csv', newline='', encoding='utf-8'))); print('Imported companies:', import_watchlist(rows))"
```

Expected behavior on the first run: two watchlist matches and two new events. On subsequent runs with unchanged demo data, no additional duplicate events should be created.

The synthetic demo does not call the live FMCSA API or Zoho CRM.

## Run automated tests in Docker

```bash
docker compose exec api python -m pytest -q
```

Verified result for this project version:

```text
15 passed
```

## Inspect the API

With the containers running, open:

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- Recent events: http://127.0.0.1:8000/events
- Run history: http://127.0.0.1:8000/runs

The recorded `docker-demo-run-20261026` entry is a synthetic test record, not a live FMCSA ingestion run.

## n8n workflow

The included n8n workflow is a demonstration scaffold. Its HTTP Request node for the API is not connected to the synthetic demo path, and scheduled live ingestion has not been verified end to end.

Zoho CRM synchronization and task creation remain disabled.

## Verification scope

These checks verify the local Docker deployment, database connectivity, synthetic event processing, duplicate prevention, API endpoints, and unit tests. They do not establish that live FMCSA ingestion, production-scale performance, scheduled n8n execution, or Zoho CRM delivery has been fully integration-tested.

This project is a portfolio prototype and is not presented as a production-ready monitoring service.