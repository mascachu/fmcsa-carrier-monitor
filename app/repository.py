from __future__ import annotations
from contextlib import contextmanager
from collections.abc import Iterator
import json
from pathlib import Path
from typing import Any
import psycopg
from psycopg.rows import dict_row
from .config import settings
from .normalize import normalize_docket, normalize_usdot

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "001_init.sql"

def connect():
    return psycopg.connect(settings.database_url, row_factory=dict_row)

def initialize_db() -> None:
    # Execute the checked-in DDL statement by statement for psycopg compatibility.
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [part.strip() for part in schema.split(";") if part.strip()]
    with connect() as conn:
        for statement in statements:
            conn.execute(statement)

def import_watchlist(rows: list[dict[str, Any]]) -> int:
    """CSV columns: company_name,usdot_number,mc_number,zoho_account_id,company_key."""
    count = 0
    with connect() as conn:
        for row in rows:
            usdot = normalize_usdot(row.get("usdot_number") or row.get("USDOT_NUMBER"))
            mc = normalize_docket(row.get("mc_number") or row.get("MC_NUMBER") or row.get("docket_number"))
            name = (row.get("company_name") or row.get("COMPANY_NAME") or "Unknown company").strip()
            external_key = (row.get("company_key") or row.get("COMPANY_KEY") or usdot or mc or "").strip()
            zoho_account_id = row.get("zoho_account_id") or row.get("ZOHO_ACCOUNT_ID")
            if not external_key or (not usdot and not mc):
                continue
            company = conn.execute(
                """INSERT INTO monitored_companies (external_company_key, company_name, zoho_account_id, is_active, updated_at)
                   VALUES (%s,%s,%s,TRUE,NOW())
                   ON CONFLICT (external_company_key) DO UPDATE SET company_name=EXCLUDED.company_name,
                     zoho_account_id=EXCLUDED.zoho_account_id, is_active=TRUE, updated_at=NOW()
                   RETURNING id""", (external_key, name, zoho_account_id)
            ).fetchone()
            company_id = company["id"]
            for typ, value in (("usdot", usdot), ("mc", mc)):
                if value:
                    conn.execute(
                        """INSERT INTO monitored_company_identifiers (company_id, identifier_type, identifier_value)
                           VALUES (%s,%s,%s)
                           ON CONFLICT (identifier_type, identifier_value) DO NOTHING""",
                        (company_id, typ, value),
                    )
            count += 1
    return count


def find_companies(conn, usdot: str | None, docket: str | None) -> list[dict[str, Any]]:
    if not usdot and not docket:
        return []

    rows = conn.execute(
        """SELECT DISTINCT c.id, c.external_company_key, c.company_name, c.zoho_account_id,
                  (SELECT i.identifier_value FROM monitored_company_identifiers i
                   WHERE i.company_id=c.id AND i.identifier_type='usdot' LIMIT 1) AS usdot_number,
                  (SELECT i.identifier_value FROM monitored_company_identifiers i
                   WHERE i.company_id=c.id AND i.identifier_type='mc' LIMIT 1) AS mc_number
           FROM monitored_companies c
           JOIN monitored_company_identifiers i ON i.company_id=c.id
           WHERE c.is_active
             AND (
               (%s::text IS NOT NULL AND i.identifier_type='usdot' AND i.identifier_value=%s::text)
               OR
               (%s::text IS NOT NULL AND i.identifier_type='mc' AND i.identifier_value=%s::text)
             )""",
        (usdot, usdot, docket, docket),
    ).fetchall()

    return rows


def get_snapshot(conn, source_name: str, record_key: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT payload FROM source_snapshots WHERE source_name=%s AND source_record_key=%s",
        (source_name, record_key),
    ).fetchone()

def upsert_snapshot(conn, source_name: str, record_key: str, usdot: str | None, docket: str | None, payload: dict[str, Any], payload_hash: str) -> None:
    conn.execute(
        """INSERT INTO source_snapshots (source_name, source_record_key, usdot_number, docket_number, payload, payload_hash)
           VALUES (%s,%s,%s,%s,%s::jsonb,%s)
           ON CONFLICT (source_name, source_record_key) DO UPDATE SET
            usdot_number=EXCLUDED.usdot_number, docket_number=EXCLUDED.docket_number,
            payload=EXCLUDED.payload, payload_hash=EXCLUDED.payload_hash, last_seen_at=NOW()""",
        (source_name, record_key, usdot, docket, json.dumps(payload), payload_hash),
    )

def insert_event(conn, event: dict[str, Any]) -> tuple[bool, int | None]:
    result = conn.execute(
        """INSERT INTO change_events
          (event_key, company_id, source_name, source_record_key, event_type, event_date, severity,
           summary, changed_fields, old_payload, new_payload)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
          ON CONFLICT (event_key) DO NOTHING RETURNING id""",
        (event["event_key"], event["company_id"], event["source_name"], event["source_record_key"],
         event["event_type"], event.get("event_date"), event["severity"], event["summary"],
         json.dumps(event.get("changed_fields", {})),
         json.dumps(event["old_payload"]) if event.get("old_payload") is not None else None,
         json.dumps(event["new_payload"])),
    ).fetchone()
    if result:
        return True, result["id"]
    existing = conn.execute("SELECT id FROM change_events WHERE event_key=%s", (event["event_key"],)).fetchone()
    return False, existing["id"] if existing else None

def pending_zoho_events(limit: int = 500) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """SELECT e.id, e.event_key, e.event_type, e.event_date, e.severity, e.summary,
                      c.external_company_key, c.company_name, c.zoho_account_id,
                      (SELECT i.identifier_value FROM monitored_company_identifiers i WHERE i.company_id=c.id AND i.identifier_type='usdot' LIMIT 1) AS usdot_number,
                      (SELECT i.identifier_value FROM monitored_company_identifiers i WHERE i.company_id=c.id AND i.identifier_type='mc' LIMIT 1) AS mc_number,
                      e.company_id
               FROM change_events e JOIN monitored_companies c ON c.id=e.company_id
               WHERE e.zoho_status IN ('pending','failed')
                 AND (SELECT COUNT(*) FROM delivery_attempts d WHERE d.event_id=e.id AND d.destination='zoho') < 3
               ORDER BY e.id LIMIT %s""", (limit,)
        ).fetchall()

def record_zoho_attempt(event_id: int, status: str, detail: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO delivery_attempts (event_id,destination,status,response_detail) VALUES (%s,'zoho',%s,%s)",
            (event_id, status, detail[:4000]),
        )
        new_status = "sent" if status == "sent" else "failed"
        conn.execute("UPDATE change_events SET zoho_status=%s WHERE id=%s", (new_status, event_id))

def start_run(run_key: str) -> int:
    with connect() as conn:
        row = conn.execute("INSERT INTO daily_runs (run_key) VALUES (%s) ON CONFLICT(run_key) DO UPDATE SET started_at=NOW(),status='running',finished_at=NULL,errors='[]'::jsonb RETURNING id", (run_key,)).fetchone()
        return row["id"]

def finish_run(run_id: int, status: str, source_counts: dict[str, int], rows_matched: int, events_created: int, errors: list[str], report_path: str | None) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE daily_runs SET finished_at=NOW(), status=%s, source_counts=%s::jsonb,
               rows_matched=%s, events_created=%s, errors=%s::jsonb, report_path=%s WHERE id=%s""",
            (status, json.dumps(source_counts), rows_matched, events_created, json.dumps(errors), report_path, run_id),
        )

def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """SELECT
                   id,
                   run_key,
                   started_at,
                   finished_at,
                   status,
                   source_counts,
                   rows_matched,
                   events_created,
                   errors,
                   report_path
               FROM daily_runs
               ORDER BY started_at DESC
               LIMIT %s""",
            (min(max(limit, 1), 200),),
        ).fetchall()



@contextmanager
def daily_run_lock() -> Iterator[bool]:
    lock_conn = connect()
    acquired = False

    try:
        result = lock_conn.execute(
            "SELECT pg_try_advisory_lock(%s) AS acquired",
            (726184205,),
        ).fetchone()

        acquired = result["acquired"]
        yield acquired

    finally:
        if acquired:
            try:
                lock_conn.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (726184205,),
                )
            finally:
                lock_conn.close()
        else:
            lock_conn.close()