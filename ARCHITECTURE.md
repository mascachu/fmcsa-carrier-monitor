# Architecture — FMCSA Change Monitoring

```text
n8n Schedule Trigger (daily)
          |
          | POST /run/daily + shared secret
          v
Python / FastAPI service
  |           |                         |
  |           +--> FMCSA public daily-difference feeds (Socrata API)
  |                                     |
  +--> Normalize USDOT / MC (docket) keys
  +--> Compare current source snapshot to incoming row
  +--> Match watched-company identifiers with indexed PostgreSQL query
  +--> Create stable, unique change-event rows
  +--> Optional Zoho custom-module upsert (disabled by default)
  +--> JSON + CSV daily run report
          |
          v
PostgreSQL
  - monitored_companies
  - monitored_company_identifiers
  - source_snapshots
  - change_events (unique event_key)
  - daily_runs
  - delivery_attempts
```

## Scale strategy for 400,000 watched companies

- Query incremental daily-difference feeds rather than fetching an individual FMCSA profile for every company.
- Normalize identifiers once during watchlist import, then match against indexed PostgreSQL identifier columns.
- Keep source snapshots and event history separate so a source-row update does not erase the previous event.
- Use deterministic event keys and database uniqueness for safe replay.
- Page through FMCSA's dataset API. Monitor row counts, run times, feed freshness, errors, and backlog.
- Confirm the client’s true watchlist distribution and measured database plan before committing to a production throughput SLA.

## Why the first version is not production-complete

The starter includes ingestion, event history, duplicate-safe event creation, reports, an n8n trigger workflow, and optional idempotent Zoho alert upsert. The client's real watchlist, Zoho custom module field names, Zoho tasks, dashboard, cloud deployment, production auth, load tests, and exact event policy still require configuration and validation.
