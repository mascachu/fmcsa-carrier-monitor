# FMCSA Daily Change Monitor

### Portfolio Case Study | Python · FastAPI · PostgreSQL · Docker · n8n

## Overview

The FMCSA Daily Change Monitor is a portfolio prototype designed to track changes in motor carrier records, match records against a watchlist, maintain event history, and prepare for future alerting workflows.

The project demonstrates API development, database integration, duplicate prevention, automated testing, workflow orchestration, and monitoring concepts.

**Project status:** Local prototype verified with synthetic data. End-to-end live ingestion and scheduled live automation remain unverified.

## The Problem

Carrier insurance and operating-authority changes can require timely review. Manually checking records and maintaining a history of changes can be repetitive and difficult to audit.

This prototype explores how a repeatable monitoring workflow could identify relevant carrier changes, preserve event history, and prepare a foundation for future notifications.

## The Solution

A containerized application built with Python, FastAPI, and PostgreSQL, supported by synthetic test data and an n8n workflow scaffold.

## Features

- **Watchlist matching:** Match carrier records using USDOT and MC identifiers.
- **Change-event tracking:** Store carrier-change events in PostgreSQL.
- **Duplicate prevention:** Avoid creating duplicate events when unchanged records are processed again.
- **Run history:** Record execution status, row counts, created-event counts, and errors.
- **API endpoints:** Expose health, source configuration, event history, and run history.
- **Automated tests:** Validate application behavior.
- **Workflow monitoring:** Demonstrate API health, event, and run-history checks through n8n.
- **Optional CRM integration:** Zoho CRM synchronization and task creation are disabled by default.
- **Human-review concept:** Demonstrate a review step before operational action.

## Architecture

1. Synthetic records enter the processing workflow.
2. The application normalizes records and matches them against the watchlist.
3. Matching changes are evaluated for event creation.
4. PostgreSQL stores event history and run metadata.
5. API endpoints expose monitoring and verification results.
6. Future integrations can support notifications and CRM synchronization.

## Verified Results

The local environment and synthetic demonstration were tested. The latest local automated test run completed successfully.

| Check | Result |
|---|---|
| Local automated test suite | 20 passed |
| Synthetic carrier rows | 2 |
| Watchlist matches in the recorded demo | 2 |
| Existing synthetic demo events retrieved | 2 |
| New events on repeated unchanged demo runs | 0 |
| Recorded demo run status | `completed` |
| Errors in the recorded demo run | 0 |
| Live FMCSA ingestion during the synthetic demo | Not performed |
| Zoho CRM synchronization during the demo | Not performed |

The repeated synthetic demo created no additional duplicate events. The recorded run history showed two matched rows and no errors.

These results describe the synthetic demonstration, not a live FMCSA monitoring run.

## FMCSA Dataset Configuration

The configured dataset identifiers are:

| Source | Dataset ID |
|---|---|
| Motus Carrier | `nakq-58th` |
| Motus Insurance History | `xe5s-wca7` |
| Motus Authority History | `dm5j-zc6c` |
| Motus Insurance | `x96h-evps` |
| Motus Revoke/Suspend | `e67p-xyd5` |

These identifiers have been checked against the official Socrata API. Configuring dataset identifiers and performing read-only source checks do not establish that complete live ingestion or production event processing has been verified.

## Run the Synthetic Demo

From the project root, start the Docker Compose services:

```bash
docker compose up -d --build
```

Run the synthetic demo:

```bash
docker compose exec api python -m scripts.run_demo
```

The demo uses synthetic carrier records from `data/sample/demo_carrier_rows.json` and the test watchlist in `data/sample/demo_watchlist.csv`.

If the demo watchlist has not yet been imported into the Docker database, run:

```bash
docker compose exec -T api python -c "import csv; from app.repository import import_watchlist; rows=list(csv.DictReader(open('/app/data/sample/demo_watchlist.csv', newline='', encoding='utf-8'))); print('Imported companies:', import_watchlist(rows))"
```

Expected behavior for a fresh synthetic dataset is two watchlist matches and two new events. Re-running unchanged demo data should not create duplicate events.

**Important:** The synthetic demo does not call the live FMCSA API or Zoho CRM.

## Run Automated Tests

Run the test suite locally:

```bash
py -3.13 -m pytest -q
```

The latest local test result was **20 passed**.

To run tests inside the Docker API container, use:

```bash
docker compose exec api python -m pytest -q
```

The Docker test result should be verified separately if the container does not contain the latest local code.

## Inspect the API

With the local FastAPI server running on port 8081, open:

- Health check: http://127.0.0.1:8081/health
- Authentication check endpoint (requires `X-Run-Token`): http://127.0.0.1:8081/auth-check
- Interactive API documentation: http://127.0.0.1:8081/docs
- Recent events: http://127.0.0.1:8081/events
- Run history: http://127.0.0.1:8081/runs
- Configured sources: http://127.0.0.1:8081/sources

The `docker-demo-run-20261026` entry is a synthetic test record, not a live FMCSA ingestion run.


For n8n running inside Docker Desktop, use the Windows-host API address: `http://host.docker.internal:8081`.

## n8n Workflow

The workflow is named **FMCSA Daily Change Monitor — Demo**.

The verified synthetic demonstration path is:

Schedule Trigger → Demo Test Data → IF → Demo Review Result → Demo Run Log

The following monitoring nodes were tested separately through manual execution:

- API Health Check
- API Auth Check
- Daily Endpoint Test
- Events Monitoring Check
- Runs Monitoring Check
- PostgreSQL connection check

The API health, authentication, source configuration, event history, run history, and PostgreSQL connection checks completed successfully.

The separate **Live FMCSA Ingestion - Manual Test** node is configured but intentionally remains unconnected and has not been executed.

A separate **FMCSA Error Notifications** workflow uses an Error Trigger connected to a Gmail notification action. It is assigned as the main workflow's error workflow. Actual email delivery has not yet been independently verified.

The main workflow remains inactive pending live-ingestion validation and final configuration review.


## Authentication Check

The API includes an `/auth-check` endpoint for validating the `X-Run-Token` header. The automated tests cover requests with missing, invalid, and valid tokens.

Protected endpoint authentication and the corresponding automated tests do not, by themselves, establish that every operational workflow has been security-reviewed for production use.

## Zoho CRM Integration

Zoho CRM synchronization and task creation are disabled. Delivery of CRM updates and tasks has not been integration-tested.

## Technology Stack

- Python 3.13
- FastAPI
- PostgreSQL
- Docker Compose
- pytest
- n8n
- FMCSA public dataset configuration
- Optional Zoho CRM integration

## Verification Scope and Limitations

Verified checks cover the local application and database setup, synthetic event processing, watchlist matching, duplicate prevention, API endpoints, automated tests, and the n8n demonstration and monitoring path.

The following remain unverified:

- End-to-end live FMCSA ingestion and processing of current source records
- Production watchlist matching using real carrier data
- Scheduled n8n execution against the live ingestion endpoint
- Zoho CRM synchronization and task delivery
- Production-scale performance, alert reliability, and operational recovery

This project is a portfolio prototype. It demonstrates the application structure, synthetic event-processing behavior, monitoring endpoints, authentication checks, and human-review workflow. It is not presented as a production-ready monitoring service.

## Next Steps

1. Validate ingestion against official FMCSA daily-difference datasets.
2. Test scheduled execution and error handling through n8n.
3. Add operational monitoring and notification delivery.
4. Validate optional CRM integration in a controlled test environment.
5. Document deployment and recovery procedures.

## Repository

[FMCSA Daily Change Monitor on GitHub](https://github.com/mascachu/fmcsa-carrier-monitor)

## Synthetic Change-Detection Demo

A controlled synthetic test changed a watchlisted carrier's operating-authority status from `Inactive` to `Active`.

| Check | Result |
|---|---|
| Synthetic record processed | 1 |
| Watchlist matches | 1 |
| Status field changed | `op_auth_status` |
| New change event created | 1 |
| Event retrieved through `GET /events` | Confirmed |
| Event severity | High |
| Live FMCSA API called by demo | No |
| Zoho CRM sync called by demo | No |

The created event was stored in PostgreSQL and returned by the event-history API. Its summary identified `op_auth_status` as the changed field.

Evidence file: [`docs/evidence/synthetic-change-events.json`](docs/evidence/synthetic-change-events.json).

This is a synthetic demonstration of the existing processing pipeline, not evidence of a live FMCSA carrier change. The demo temporarily overrides baseline mode within its own Python process; the normal API configuration remains unchanged.

## n8n Workflow — Portfolio Demo

### Overview

The n8n prototype includes a synthetic demonstration workflow, separately tested monitoring nodes, and a separate error-notification workflow.

### Verified Demo Path

`Schedule Trigger → Demo Test Data → IF → Demo Review Result → Demo Run Log`

The main workflow is currently inactive. Its schedule is configured for 7:00 AM Asia/Manila time but has not been activated for scheduled operation.

### Monitoring Checks

The following checks were executed separately and completed successfully:

- API health check
- API authentication check
- Configured FMCSA source check
- Event-history check
- Run-history check
- PostgreSQL connection check

These monitoring nodes are not connected to the synthetic demo path.

### Live Ingestion Safety

The `Live FMCSA Ingestion - Manual Test` node is configured but remains disconnected and has not been executed through n8n.

Live ingestion must be validated separately before scheduled automation is enabled.

### Error Notifications

The separate `FMCSA Error Notifications` workflow connects an Error Trigger to a Gmail notification action. It is assigned as the main workflow's error workflow.

Actual email delivery has not yet been independently verified. The error-notification workflow has not been validated through a controlled real failure.

### Safety and Scope

- The n8n demo path uses synthetic data.
- Monitoring checks were tested separately.
- Live FMCSA ingestion through n8n has not been performed.
- Zoho CRM synchronization and task creation remain disabled.
- The main workflow remains inactive pending further testing and review.

### Current Status

The synthetic demo path, monitoring endpoints, and PostgreSQL connection have been verified. Scheduled live ingestion and end-to-end error email delivery remain unverified.
