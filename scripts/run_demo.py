from __future__ import annotations

import json
from pathlib import Path

from app.processor import process_record
from app.repository import connect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_FILE = PROJECT_ROOT / "data" / "sample" / "demo_carrier_rows.json"


def main() -> None:
    rows = json.loads(DEMO_FILE.read_text(encoding="utf-8"))

    with connect() as conn:
        total_matched = 0
        total_events = 0

        for row in rows:
            result = process_record(conn, "motus_carrier", row)
            total_matched += result["matched_companies"]
            total_events += result["events_created"]

            print(
                f"Record {result['record_key']}: "
                f"matched={result['matched_companies']}, "
                f"events_created={result['events_created']}"
            )

    print("\nSynthetic demo complete.")
    print(f"Records processed: {len(rows)}")
    print(f"Watchlist matches: {total_matched}")
    print(f"New events created: {total_events}")
    print("Live FMCSA API called: No")
    print("Zoho sync called: No")


if __name__ == "__main__":
    main()