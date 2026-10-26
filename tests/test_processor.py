from app.processor import event_type_and_summary
from app.normalize import row_identifiers


def test_synthetic_demo_carrier_matches_watchlist_identifiers():
    row = {
        "docket_number": "MC000123456",
        "usdot_number": "9999001",
        "op_auth_type": "Common",
        "op_auth_status": "Inactive",
        "bipd_file": "N",
        "legal_name": "Example Carrier One LLC",
    }

    usdot, docket, _ = row_identifiers("motus_carrier", row)

    assert usdot == "9999001"
    assert docket == "MC123456"


def test_synthetic_demo_carrier_generates_expected_event():
    row = {
        "docket_number": "MC000123456",
        "usdot_number": "9999001",
        "op_auth_type": "Common",
        "op_auth_status": "Inactive",
        "bipd_file": "N",
        "legal_name": "Example Carrier One LLC",
    }

    event_type, summary, severity = event_type_and_summary(
        "motus_carrier",
        row,
        {
            "op_auth_status": {"old": "Active", "new": "Inactive"},
            "bipd_file": {"old": "Y", "new": "N"},
        },
    )

    assert event_type == "CARRIER_RECORD_CHANGE"
    assert "op_auth_status" in summary
    assert "bipd_file" in summary
    assert severity == "high"
from unittest.mock import MagicMock
from app.repository import insert_event


def test_insert_event_duplicate_is_not_created():
    conn = MagicMock()

    # Simulate an event_key conflict: INSERT returns no row.
    conn.execute.return_value.fetchone.side_effect = [
        None,
        {"id": 42},
    ]

    event = {
        "event_key": "a" * 64,
        "company_id": 1,
        "source_name": "motus_carrier",
        "source_record_key": "9999001|MC123456",
        "event_type": "CARRIER_RECORD_CHANGE",
        "event_date": None,
        "severity": "high",
        "summary": "Carrier authority status changed.",
        "changed_fields": {
            "op_auth_status": {"old": "Active", "new": "Inactive"}
        },
        "old_payload": {"op_auth_status": "Active"},
        "new_payload": {"op_auth_status": "Inactive"},
    }

    created, event_id = insert_event(conn, event)

    assert created is False
    assert event_id == 42
    assert conn.execute.call_count == 2