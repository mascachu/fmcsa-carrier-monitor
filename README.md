# FMCSA Daily Change Monitor — Portfolio Prototype

A staged proof-of-concept for an FMCSA carrier insurance/authority monitoring system. It uses Python + FastAPI, PostgreSQL history, official FMCSA daily-difference feeds published through the U.S. DOT Open Data Portal, an n8n schedule trigger, and an optional Zoho CRM upsert integration.

> \\\*\\\*Status:\\\*\\\* starter prototype, not production-ready. No live company database, Zoho credentials, or hosting account is included. The sample watchlist values are synthetic. Validate current dataset schemas, source timing, and business rules before enabling real alerts.

## Architecture

1. **FMCSA sources:** fetch daily-difference datasets for Motus Carrier, InsHist, AuthHist, Insur, and RevokeSuspend from the public DOT data API.
2. **Python ingestion:** page through Socrata JSON endpoints and normalize USDOT/MC (docket) keys.
3. **PostgreSQL:** keep a watchlist, latest source snapshots, immutable change-event ledger, run summaries, and delivery attempts.
4. **Matching:** compare normalized USDOT and MC/docket identifiers against indexed watchlist columns.
5. **Duplicate prevention:** deterministic SHA-256 event keys plus a PostgreSQL unique constraint prevent the same source event from creating multiple event records. Production send logic should use an idempotent Zoho custom-module upsert, too.
6. **n8n:** daily Schedule Trigger calls the protected API endpoint. Import `n8n/fmcsa\\\_daily\\\_monitor.json`, then set the schedule and token to match the deployment.
7. **Zoho CRM:** optional custom-module upsert is disabled by default. Configure and test module fields before enabling.
8. **Report:** each run writes JSON and CSV summaries under `reports/`.

## Official daily-difference data sources

* Motus Carrier — `nakq-58th`
* Motus InsHist — `xe5s-wca7`
* Motus AuthHist — `dm5j-zc6c`
* Motus Insur — `x96h-evps`
* Motus RevokeSuspend — `e67p-xyd5`

FMCSA says its active operating-authority data now uses the modern MOTUS schema and publishes daily-difference datasets. Carrier records may have multiple docket numbers per USDOT number, so do **not** treat a USDOT number as a one-row-per-authority key. The daily feeds are snapshots/deltas, not guaranteed real-time legal status. See the official sources:

* https://www.fmcsa.dot.gov/registration/fmcsa-data-dissemination-program
* https://data.transportation.gov/Trucking-and-Motorcoaches/Motus-Carrier/nakq-58th
* https://data.transportation.gov/Trucking-and-Motorcoaches/Motus-InsHist/xe5s-wca7
* https://data.transportation.gov/Trucking-and-Motorcoaches/Motus-AuthHist/dm5j-zc6c

## Local setup (Docker)

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Set a strong `POSTGRES\\\_PASSWORD` and a long random `FMCSA\\\_RUN\\\_TOKEN`. Keep `.env` private.
4. Start services:

```bash
   docker compose up --build -d
   ```

5. Check health: `http://localhost:8000/health`.
6. Import your **authorized** watchlist CSV (columns: `company\\\_name,usdot\\\_number,mc\\\_number,zoho\\\_account\\\_id`). Sample rows are fake. From a shell inside the API container:

```bash
   docker compose exec api python -m app.import\\\_watchlist /app/data/watchlist.example.csv
   ```

7. Run a daily ingestion test manually (this does call public FMCSA data; Zoho is still off):

```bash
   curl -X POST http://localhost:8000/run/daily \\\\
     -H 'X-Run-Token: YOUR\\\_FMCSA\\\_RUN\\\_TOKEN'
   ```

8. See latest detected events: `http://localhost:8000/events`.
9. Reports are written under `reports/` on the host.

The API binds to `127.0.0.1` by default through Docker. Do not expose it publicly without HTTPS, secrets management, access controls, rate limiting, monitoring, and cloud-network restrictions.

## Normalization and event rules

* USDOT values are normalized as digits.
* Docket values are normalized so `123`, `MC123`, and `MC000123` match as `MC123` (similar for FF/MX).
* `Motus InsHist` creates a cancellation/replacement/history event for a watched company when a new source-history row is first seen.
* `Motus AuthHist` creates an authority history event when a new history record is first seen.
* `Motus RevokeSuspend` creates a suspension/revocation event for a watched company when a new source row is first seen.
* `Motus Carrier` / `Motus Insur` compare a row against its previous snapshot and emit a source-change event when first observed or changed.

These mappings are a starting point. Confirm source field definitions, blank-string semantics, record keys, and event severity against the attached FMCSA data dictionaries before use with live customers. In particular, insurance cancellation and replacement should be driven by InsHist reason/date fields, not inferred solely from a missing active-policy row.

## Zoho setup (optional; disabled by default)

Before enabling `ZOHO\\\_SYNC\\\_ENABLED=true`, create a custom module (API name default `FMCSA\\\_Alerts`) with these API field names, and mark `Event\\\_Key` as a unique field:

* `Name` (standard name field)
* `Event\\\_Key` (unique text)
* `USDOT\\\_Number` (text)
* `MC\\\_Number` (text)
* `Event\\\_Type` (picklist or text)
* `Event\\\_Date` (date or text, based on target CRM setup)
* `Description` (multi-line text)
* `Severity` (picklist/text)

Configure OAuth refresh-token credentials and correct regional Zoho API/accounts domains. Start in a Zoho sandbox/test org. Validate the custom module upsert response and failure handling before production. The provided integration supports custom-module alert upsert. Optional high-severity follow-up Tasks are disabled by default; to enable them, configure `ZOHO\\\_TASKS\\\_ENABLED=true` and create a unique custom field on the Tasks module matching `ZOHO\\\_TASK\\\_EVENT\\\_KEY\\\_FIELD\\\_API\\\_NAME` (default `FMCSA\\\_Event\\\_Key`). Task upsert/account association must be tested in the client's Zoho sandbox, and dashboards still require field/report configuration in the target CRM org. Failed Zoho deliveries are retried on subsequent daily runs up to three recorded attempts.

## n8n Setup and Current Demo Status

n8n is configured locally through Docker Compose and is available at `http://127.0.0.1:5678`.

### Current workflow

- A Schedule Trigger is configured for 7:00 AM in the `Asia/Manila` timezone.
- Demo data is passed through an IF node to check whether `approval_status` equals `pending_review`.
- The true and false branches produce separate review-result values.
- The HTTP Request node targeting `http://api:8000/run/daily` is currently disconnected from the demo branches.

### Safety and limitations

- The workflow is intended for portfolio demonstration and has not been confirmed as a complete scheduled ingestion workflow.
- The workflow should remain unpublished and unexecuted until the watchlist, API authentication, and execution paths have been reviewed.
- The demo branch uses synthetic data and does not call the live FMCSA API.
- Zoho CRM synchronization and task creation remain disabled.
- Before activation, connect and test the intended API path safely, verify the run token without exposing it, and review error handling and duplicate prevention.


## Tests

Run unit tests locally from the project root:

```bash
python -m pip install -r requirements.txt
pytest -q
```

The unit tests cover key normalization and field-level diff detection. They do not prove full integration with live FMCSA feeds or Zoho CRM.

## Before calling this production-ready

* Confirm current FMCSA data dictionaries / field aliases and that each required event is covered by the correct feed.
* Build a baseline snapshot safely before enabling customer alerts (avoid alerting on every existing record at first load).
* Import the real authorized 400,000-record watchlist and validate USDOT/MC key uniqueness, normalization, and query performance.
* Add a one-time baseline mode, stale-source checks, source row-count thresholds, full run locking, and alert-on-failed-run notifications.
* Implement Zoho Tasks and dashboards with the client's exact module/field configuration.
* Add integration tests, load tests, replay tests, dead-letter review, secret management, HTTPS, backups, and observability.
* Compare sampled carrier changes against FMCSA Licensing \& Insurance and documented authoritative data before issuing business-critical alerts.

\## Docker Verification and Synthetic Demo



The Docker deployment was verified locally using Docker Compose and a PostgreSQL container.



\### Verified checks



\- Docker API container starts successfully.

\- PostgreSQL container reports healthy status.

\- `GET /health` returns HTTP 200 with service status `ok`.

\- `GET /sources` returns the configured FMCSA daily-difference dataset identifiers.

\- Synthetic demo records match the configured test watchlist.

\- The first synthetic demo run creates two change events.

\- Re-running the same demo creates zero additional duplicate events.

\- `GET /events` returns the two stored demo events.

\- A synthetic run-history record can be retrieved through `GET /runs`.

\- Automated test suite: \*\*15 passed\*\* in the Docker container.

\- Zoho synchronization and task creation remain disabled during the demo.



\### Run the synthetic demo



Ensure Docker Compose services are running, then execute from the project root:



```bash

docker compose up -d --build

docker compose exec api python -m scripts.run\\\_demo

```



The demo uses synthetic carrier records from `data/sample/demo\\\_carrier\\\_rows.json` and the test watchlist in `data/sample/demo\\\_watchlist.csv`.



Import the demo watchlist into the Docker database before running the demo if it has not already been imported:



```bash

docker compose exec -T api python -c "import csv; from app.repository import import\\\_watchlist; rows=list(csv.DictReader(open('/app/data/sample/demo\\\_watchlist.csv', newline='', encoding='utf-8'))); print('Imported companies:', import\\\_watchlist(rows))"

```



Expected behavior on the first run: two watchlist matches and two new events. On subsequent runs with unchanged demo data, no additional duplicate events should be created.



The synthetic demo does not call the live FMCSA API or Zoho CRM.



\### Run automated tests in Docker



```bash

docker compose exec api python -m pytest -q

```



The verified result for this project version was:



```text

15 passed

```



\### Inspect the API



With the containers running, open:



\- Health check: http://127.0.0.1:8000/health

\- Interactive API documentation: http://127.0.0.1:8000/docs

\- Recent events: http://127.0.0.1:8000/events

\- Run history: http://127.0.0.1:8000/runs



The recorded `docker-demo-run-20261026` entry is a synthetic test record, not a live FMCSA ingestion run.



\### Verification scope



These checks verify the local Docker deployment, database connectivity, synthetic event processing, duplicate prevention, API endpoints, and unit tests. They do not establish that live FMCSA ingestion, production-scale performance, scheduled n8n execution, or Zoho CRM delivery has been fully integration-tested.

