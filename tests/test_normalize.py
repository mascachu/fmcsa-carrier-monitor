from app.normalize import normalize_usdot, normalize_docket, row_identifiers, diff_fields

def test_normalize_usdot():
    assert normalize_usdot("000123") == "123"
    assert normalize_usdot("USDOT 456") == "456"

def test_normalize_docket():
    assert normalize_docket("12345") == "MC12345"
    assert normalize_docket("MC00012345") == "MC12345"
    assert normalize_docket("FF00000077") == "FF77"

def test_stable_carrier_key():
    a = {"USDOT_NUMBER": "000123", "DOCKET_NUMBER": "MC00077"}
    b = {"usdot_number": "123", "docket_number": "MC77"}
    assert row_identifiers("motus_carrier", a)[2] == row_identifiers("motus_carrier", b)[2]

def test_diff_fields_detects_status_change():
    old = {"op_auth_status": "Active", "bipd_file": "Y"}
    new = {"op_auth_status": "Inactive", "bipd_file": "Y"}
    diff = diff_fields(old, new)
    assert diff["op_auth_status"] == {"old": "Active", "new": "Inactive"}
    assert "bipd_file" not in diff
from app.processor import event_type_and_summary


def test_inactive_authority_status_creates_high_severity_event():
    row = {
        "op_auth_status": "Inactive",
        "reason": "Status changed",
    }

    event_type, summary, severity = event_type_and_summary(
        "motus_authhist",
        row,
        {"op_auth_status": {"old": "Active", "new": "Inactive"}},
    )

    assert event_type == "AUTHORITY_STATUS_CHANGE"
    assert "Inactive" in summary
    assert severity == "high"


def test_carrier_status_change_creates_high_severity_event():
    row = {
        "op_auth_status": "Inactive",
        "bipd_file": "N",
    }

    event_type, summary, severity = event_type_and_summary(
        "motus_carrier",
        row,
        {"op_auth_status": {"old": "Active", "new": "Inactive"}},
    )

    assert event_type == "CARRIER_RECORD_CHANGE"
    assert "op_auth_status" in summary
    assert severity == "high"