from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from app.config import settings
from app.normalize import normalized_row, row_identifiers
from app.processor import process_record
from app.repository import connect, get_snapshot

demo_file = Path("/app/data/sample/demo_carrier_rows.json")
if not demo_file.exists():
    demo_file = Path("data/sample/demo_carrier_rows.json")

rows = json.loads(demo_file.read_text(encoding="utf-8"))
row = rows[0]
source = "motus_carrier"

normalized = normalized_row(row)
usdot, docket, record_key = row_identifiers(source, normalized)

with connect() as conn:
    existing = get_snapshot(conn, source, record_key)
    if not existing:
        raise SystemExit(
            "No existing snapshot. Run the synthetic baseline demo first."
        )

    old_payload = existing["payload"]
    old_status = old_payload.get("op_auth_status")
    if not old_status:
        raise SystemExit("Existing snapshot has no authority status.")

    new_status = (
        "Inactive" if str(old_status).lower() != "inactive" else "Active"
    )
    row["op_auth_status"] = new_status

    # Use an independent settings copy for this synthetic demo only.
    import app.processor as processor
    processor.settings = replace(settings, baseline_mode=False)

    result = process_record(conn, source, row)

    print("Synthetic change demo complete.")
    print(f"Record key: {record_key}")
    print(f"Previous status: {old_status}")
    print(f"New status: {new_status}")
    print(f"Watchlist matches: {result['matched_companies']}")
    print(f"New events created: {result['events_created']}")
    print("Live FMCSA API called: No")
    print("Zoho sync called: No")
