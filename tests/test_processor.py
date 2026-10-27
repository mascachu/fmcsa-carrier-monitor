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

def test_baseline_mode_does_not_emit_events(monkeypatch):
    from unittest.mock import MagicMock
    from dataclasses import replace
    import app.processor as processor

    monkeypatch.setattr(
        processor,
        "settings",
        replace(processor.settings, baseline_mode=True),
    )

    conn = MagicMock()
    conn.transaction.return_value.__enter__.return_value = None

    monkeypatch.setattr(processor, "get_snapshot", lambda *args: None)
    monkeypatch.setattr(processor, "find_companies", lambda *args: [{"id": 1}])

    snapshot_mock = MagicMock()
    monkeypatch.setattr(processor, "upsert_snapshot", snapshot_mock)

    insert_event_mock = MagicMock()
    monkeypatch.setattr(processor, "insert_event", insert_event_mock)

    result = processor.process_record(
        conn,
        "motus_carrier",
        {
            "usdot_number": "9999001",
            "docket_number": "MC000123456",
            "legal_name": "Example Carrier One LLC",
            "op_auth_status": "Active",
        },
    )

    assert result["matched_companies"] == 1
    assert result["events_created"] == 0
    insert_event_mock.assert_not_called()
    snapshot_mock.assert_called_once()


def test_unchanged_record_does_not_create_duplicate_event(monkeypatch):
    from unittest.mock import MagicMock
    import app.processor as processor

    row = {
        "usdot_number": "9999001",
        "docket_number": "MC000123456",
        "legal_name": "Example Carrier One LLC",
        "op_auth_status": "Active",
    }

    normalized = processor.normalized_row(row)

    monkeypatch.setattr(
        processor,
        "settings",
        __import__("dataclasses").replace(
            processor.settings,
            baseline_mode=False,
        ),
    )
    monkeypatch.setattr(
        processor,
        "get_snapshot",
        lambda *args: {"payload": normalized},
    )
    monkeypatch.setattr(
        processor,
        "find_companies",
        lambda *args: [{"id": 1}],
    )

    upsert_mock = MagicMock()
    monkeypatch.setattr(processor, "upsert_snapshot", upsert_mock)

    insert_mock = MagicMock()
    monkeypatch.setattr(processor, "insert_event", insert_mock)

    result = processor.process_record(
        MagicMock(),
        "motus_carrier",
        row,
    )

    assert result["matched_companies"] == 1
    assert result["events_created"] == 0
    insert_mock.assert_not_called()
    upsert_mock.assert_called_once()


def test_changed_carrier_status_creates_high_severity_event(monkeypatch):
    from dataclasses import replace
    from unittest.mock import MagicMock
    import app.processor as processor

    old_row = {
        "usdot_number": "9999001",
        "docket_number": "MC000123456",
        "legal_name": "Example Carrier One LLC",
        "op_auth_status": "Active",
        "bipd_file": "Y",
    }
    new_row = {
        **old_row,
        "op_auth_status": "Inactive",
        "bipd_file": "N",
    }

    monkeypatch.setattr(
        processor,
        "settings",
        replace(processor.settings, baseline_mode=False),
    )
    monkeypatch.setattr(
        processor,
        "get_snapshot",
        lambda *args: {"payload": old_row},
    )
    monkeypatch.setattr(
        processor,
        "find_companies",
        lambda *args: [{"id": 1}],
    )
    monkeypatch.setattr(
        processor,
        "insert_event",
        lambda *args: (True, 101),
    )

    snapshot_mock = MagicMock()
    monkeypatch.setattr(processor, "upsert_snapshot", snapshot_mock)

    result = processor.process_record(
        MagicMock(),
        "motus_carrier",
        new_row,
    )

    assert result["matched_companies"] == 1
    assert result["events_created"] == 1
    snapshot_mock.assert_called_once()