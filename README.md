# FMCSA Daily Change Monitor

### Portfolio Case Study | Python · FastAPI · PostgreSQL · Docker · n8n

## Overview

The FMCSA Daily Change Monitor is a portfolio prototype designed to track changes in motor carrier records, match records against a watchlist, maintain event history, and support future alerting workflows.

The project demonstrates API development, database integration, duplicate prevention, automated testing, and workflow orchestration concepts.

**Project status:** Local prototype verified with synthetic data. Live ingestion and end-to-end scheduled automation remain to be validated.

## The Problem

Carrier insurance and operating-authority changes can require timely review. Manually checking records and maintaining a history of changes can be repetitive and difficult to audit.

This prototype explores how a repeatable monitoring workflow could identify relevant carrier changes, preserve event history, and prepare a foundation for future notifications.

## The Solution

I built a containerized application using Python, FastAPI, and PostgreSQL, with a synthetic-data demo and an n8n workflow scaffold.

## Features

- **Watchlist matching:** Match test carrier records using USDOT and MC identifiers.
- **Change-event tracking:** Store carrier-change events in PostgreSQL.
- **Duplicate prevention:** Avoid creating duplicate events when unchanged synthetic records are processed again.
- **Run history:** Record execution status, row counts, created-event counts, and errors.
- **API endpoints:** Expose health, source configuration, event history, and run history.
- **Automated tests:** Validate application behavior.
- **Workflow extensibility:** Include an n8n scaffold and optional Zoho CRM integration configuration.

## Architecture

1. Synthetic records enter the processing workflow.
2. The application normalizes records and matches them against the watchlist.
3. Matching changes are evaluated for event creation.
4. PostgreSQL stores event history and run metadata.
5. API endpoints expose monitoring and verification results.
6. Future integrations can support notifications and CRM synchronization.

## Verified Results

The local Docker environment was verified using synthetic carrier records.

| Check | Result |
|---|---|
| Automated test suite | 15 passed |
| Synthetic records processed | 2 |
| Watchlist matches | 2 |
| Existing demo events retrieved | 2 |
| New events on repeated demo runs | 0 |
| Run-history status | `completed` |
| Errors in recorded demo run | 0 |
| Live FMCSA API called during demo | No |
| Zoho sync called during demo | No |

The repeated demo produced no additional events, consistent with the expected duplicate-prevention behavior. The run-history endpoint returned a completed synthetic run with two matched rows and no errors.

## Run the Synthetic Demo

Ensure Docker Compose services are running, then execute from the project root:

```bash
docker compose up -d --build
docker compose exec api python -m scripts.run_demo
```

The demo uses synthetic carrier records from `data/sample/demo_carrier_rows.json` and the test watchlist in `data/sample/demo_watchlist.csv`.

If the demo watchlist has not yet been imported into the Docker database, run:

```bash
docker compose exec -T api python -c "import csv; from app.repository import import_watchlist; rows=list(csv.DictReader(open('/app/data/sample/demo_watchlist.csv', newline='', encoding='utf-8'))); print('Imported companies:', import_watchlist(rows))"
```

Expected behavior on the first run: two watchlist matches and two new events. On subsequent runs with unchanged demo data, no additional duplicate events should be created.

The synthetic demo does not call the live FMCSA API or Zoho CRM.

## Run Automated Tests

```bash
docker compose exec api python -m pytest -q
```

Verified result:

```text
15 passed
```

## Inspect the API

With the containers running, open:

- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Recent events: [http://127.0.0.1:8000/events](http://127.0.0.1:8000/events)
- Run history: [http://127.0.0.1:8000/runs](http://127.0.0.1:8000/runs)

The recorded `docker-demo-run-20261026` entry is a synthetic test record, not a live FMCSA ingestion run.

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- Docker Compose
- pytest
- n8n workflow scaffold
- FMCSA public dataset configuration

## Safety and Scope

The current verification covers the local Docker environment, database connectivity, synthetic record processing, watchlist matching, event history, duplicate prevention, API endpoints, and automated tests.

The prototype does not yet establish end-to-end live FMCSA ingestion, production-scale reliability, scheduled n8n execution, or Zoho CRM delivery. The n8n HTTP Request node is not connected to the synthetic demo path. CRM synchronization and task creation remain disabled.

This project is a portfolio prototype and is not presented as a production-ready monitoring service.

## What I Learned

- Designing APIs around a persistent relational database
- Testing event-processing and duplicate-prevention behavior
- Tracking execution history for observability
- Managing local services using Docker Compose
- Documenting verification evidence and limitations
- Separating a safe synthetic demo from future live integrations

## Next Steps

1. Validate ingestion against official FMCSA daily-difference datasets.
2. Test scheduled execution and error handling through n8n.
3. Add operational monitoring and notification delivery.
4. Validate optional CRM integration in a controlled test environment.
5. Document deployment and recovery procedures.

## Repository

[FMCSA Daily Change Monitor on GitHub](https://github.com/mascachu/fmcsa-carrier-monitor)
