
from __future__ import annotations

from datetime import date
from typing import Any

import psycopg

from .normalize import (
    diff_fields,
    normalized_row,
    row_identifiers,
    sha256_text,
    stable_json,
)
from .config import settings
from .repository import (
    find_companies,
    get_snapshot,
    upsert_snapshot,
    insert_event,
)


def event_type_and_summary(
    source_name: str,
    row: dict[str, Any],
    changes: dict[str, Any],
) -> tuple[str, str, str]:
    r = normalized_row(row)

    if source_name == "motus_inshist":
        reason = str(r.get("filing_status_reason") or "changed").strip().lower()
        event_type = {
            "cancelled": "INSURANCE_CANCELLED",
            "canceled": "INSURANCE_CANCELLED",
            "replaced": "INSURANCE_REPLACED",
            "transferred": "INSURANCE_TRANSFERRED",
            "name change": "INSURANCE_NAME_CHANGE",
        }.get(reason, "INSURANCE_HISTORY_EVENT")
        policy = r.get("policy_no") or "unknown policy"
        summary = f"FMCSA insurance filing {reason} for policy {policy}."
        severity = (
            "high"
            if reason in {"cancelled", "canceled", "replaced"}
            else "medium"
        )

    elif source_name == "motus_authhist":
        event_type = "AUTHORITY_STATUS_CHANGE"
        status = r.get("op_auth_status") or "status not supplied"
        reason = r.get("reason") or "FMCSA authority history update"
        summary = f"Authority history update: status={status}; reason={reason}."
        severity = (
            "high"
            if any(
                term in str(status).lower()
                for term in ("inactive", "revoked", "suspend")
            )
            else "medium"
        )

    elif source_name == "motus_revokesuspend":
        event_type = "AUTHORITY_SUSPENSION_OR_REVOCATION"
        order_type = r.get("order1_type_desc") or "order type not supplied"
        effective_date = r.get("order1_effective_date") or "date not supplied"
        serve_date = r.get("order1_serve_date") or "date not supplied"
        summary = (
            f"FMCSA revocation/suspension feed reports "
            f"order={order_type}; effective_date={effective_date}; "
            f"serve_date={serve_date}."
        )
        severity = "high"

    elif source_name == "motus_insur":
        event_type = "INSURANCE_POLICY_UPDATE"
        company = (
            r.get("insurance_company_name")
            or "insurance carrier not supplied"
        )
        policy = r.get("policy_no") or "unknown policy"
        summary = (
            f"FMCSA insurance feed updated policy {policy}; insurer={company}."
        )
        severity = "medium"

    else:
        event_type = "CARRIER_RECORD_CHANGE"
        changed_names = (
            ", ".join(changes.keys())
            if changes
            else "new daily-difference record"
        )
        summary = (
            "FMCSA carrier daily-difference record updated. "
            f"Changed fields: {changed_names}."
        )
        severity = (
            "high"
            if any(
                key in changes
                for key in (
                    "op_auth_status",
                    "bipd_file",
                    "cargo_file",
                    "bond_file",
                )
            )
            else "medium"
        )

    return event_type, summary, severity


def event_date_or_none(row: dict[str, Any]) -> date | None:
    r = normalized_row(row)

    for key in (
        "cancl_effective_date",
        "status_change_date",
        "order1_effective_date",
        "trans_date",
        "effective_date",
    ):
        value = r.get(key)
        if not value:
            continue

        text_value = str(value).strip()

        if len(text_value) == 8 and text_value.isdigit():
            try:
                return date(
                    int(text_value[:4]),
                    int(text_value[4:6]),
                    int(text_value[6:8]),
                )
            except ValueError:
                continue

        try:
            return date.fromisoformat(text_value[:10])
        except ValueError:
            continue

    return None


def process_record(
    conn: psycopg.Connection,
    source_name: str,
    raw_record: dict[str, Any],
) -> dict[str, Any]:
    """Process one official daily-difference row transactionally and idempotently."""
    row = normalized_row(raw_record)
    usdot, docket, source_record_key = row_identifiers(source_name, row)
    payload_hash = sha256_text(stable_json(row))
    created = 0

    with conn.transaction():
        old_result = get_snapshot(conn, source_name, source_record_key)
        old_payload = old_result["payload"] if old_result else None
        changes = diff_fields(old_payload, row)
        matched_companies = find_companies(conn, usdot, docket)

        if matched_companies:
            should_emit = (
                not settings.baseline_mode
                and old_payload is not None
                and bool(changes)
            )

            if should_emit:
                event_type, summary, severity = event_type_and_summary(
                    source_name, row, changes
                )
                event_key_base = sha256_text(
                    stable_json(
                        {
                            "source": source_name,
                            "source_record_key": source_record_key,
                            "event_type": event_type,
                            "payload": row,
                            "old_payload": old_payload if changes else None,
                        }
                    )
                )

                for company in matched_companies:
                    created_now, _ = insert_event(
                        conn,
                        {
                            "event_key": sha256_text(
                                f"{event_key_base}:{company['id']}"
                            ),
                            "company_id": company["id"],
                            "source_name": source_name,
                            "source_record_key": source_record_key,
                            "event_type": event_type,
                            "event_date": event_date_or_none(row),
                            "severity": severity,
                            "summary": summary,
                            "changed_fields": changes,
                            "old_payload": old_payload,
                            "new_payload": row,
                        },
                    )
                    created += int(created_now)

            upsert_snapshot(
                conn,
                source_name,
                source_record_key,
                usdot,
                docket,
                row,
                payload_hash,
            )

    return {
        "matched_companies": len(matched_companies),
        "events_created": created,
        "record_key": source_record_key,
    }
