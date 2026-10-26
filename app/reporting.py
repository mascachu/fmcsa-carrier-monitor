from __future__ import annotations
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .repository import connect

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"

def write_daily_report(run_id: int, run_key: str, status: str, source_counts: dict[str,int], rows_matched: int, events_created: int, errors: list[str]) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_DIR / f"daily_report_{stamp}.json"
    report = {
        "run_id": run_id, "run_key": run_key, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status, "source_counts": source_counts, "rows_matched_to_watchlist": rows_matched,
        "new_events_created": events_created, "errors": errors,
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    csv_path = path.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["run_id", run_id]); writer.writerow(["run_key", run_key]); writer.writerow(["status", status])
        writer.writerow(["rows_matched_to_watchlist", rows_matched]); writer.writerow(["new_events_created", events_created])
        for source, count in source_counts.items(): writer.writerow([f"source_rows:{source}", count])
        for i, err in enumerate(errors, 1): writer.writerow([f"error_{i}", err])
    return str(path)


def latest_events(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """SELECT
                   e.id,
                   e.event_key,
                   c.company_name,
                   (SELECT i.identifier_value
                    FROM monitored_company_identifiers i
                    WHERE i.company_id = c.id
                      AND i.identifier_type = 'usdot'
                    LIMIT 1) AS usdot_number,
                   (SELECT i.identifier_value
                    FROM monitored_company_identifiers i
                    WHERE i.company_id = c.id
                      AND i.identifier_type = 'mc'
                    LIMIT 1) AS mc_number,
                   e.source_name,
                   e.event_type,
                   e.event_date,
                   e.severity,
                   e.summary,
                   e.zoho_status,
                   e.created_at
               FROM change_events e
               JOIN monitored_companies c ON c.id = e.company_id
               ORDER BY e.created_at DESC
               LIMIT %s""",
            (limit,),
        ).fetchall()
