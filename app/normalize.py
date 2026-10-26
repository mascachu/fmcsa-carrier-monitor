from __future__ import annotations
import hashlib
import json
import re
from typing import Any


def normalize_usdot(value: Any) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    return digits.lstrip("0") or "0"


def normalize_docket(value: Any) -> str | None:
    """Normalize '12345', 'MC12345' and FMCSA-style 'MC00012345' to MC12345."""
    if value is None:
        return None
    raw = re.sub(r"[^A-Z0-9]", "", str(value).upper())
    if not raw:
        return None
    match = re.fullmatch(r"(MC|FF|MX)?0*(\d+)", raw)
    if not match:
        return raw
    prefix = match.group(1) or "MC"
    number = match.group(2).lstrip("0") or "0"
    return f"{prefix}{number}"


def normalized_row(row: dict[str, Any]) -> dict[str, Any]:
    """Socrata JSON keys are usually lowercase; normalize key casing only."""
    return {str(k).lower(): v for k, v in row.items()}


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def row_identifiers(source_name: str, record: dict[str, Any]) -> tuple[str | None, str | None, str]:
    row = normalized_row(record)
    usdot = normalize_usdot(row.get("usdot_number") or row.get("dot_number"))
    docket = normalize_docket(row.get("docket_number") or row.get("mc_number"))

    if source_name == "motus_carrier":
        parts = [usdot, docket]
    elif source_name == "motus_inshist":
        parts = [usdot, docket, row.get("policy_no"), row.get("cancl_effective_date"), row.get("filing_status_reason"), row.get("effective_date")]
    elif source_name == "motus_authhist":
        parts = [usdot, docket, row.get("status_change_date"), row.get("op_auth_type"), row.get("op_auth_status"), row.get("reason")]
    elif source_name == "motus_insur":
        parts = [usdot, docket, row.get("policy_no"), row.get("effective_date"), row.get("trans_date"), row.get("ins_form_code")]
    elif source_name == "motus_revokesuspend":
        parts = [usdot, docket, row.get("op_auth_type"), row.get("order1_effective_date"), row.get("order1_serve_date"), row.get("reason")]
    else:
        parts = [usdot, docket, sha256_text(stable_json(row))]

    # Don't include missing identifiers as ambiguous empty values. If a source does not
    # provide enough identity fields, fall back to a full-row hash to avoid overwriting
    # different events for the same USDOT/MC pair.
    key = "|".join("" if p is None else str(p).strip() for p in parts)
    if not usdot and not docket:
        key = sha256_text(stable_json(row))
    elif len(parts) > 2 and not any(p not in (None, "") for p in parts[2:]):
        key = f"{usdot or ''}|{docket or ''}|{sha256_text(stable_json(row))}"
    return usdot, docket, key


def diff_fields(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    old = normalized_row(old or {})
    new = normalized_row(new)
    ignored = {"last_seen_at", "retrieved_at"}
    changes: dict[str, dict[str, Any]] = {}
    for key in sorted(set(old) | set(new)):
        if key in ignored:
            continue
        before = old.get(key)
        after = new.get(key)
        if before != after:
            changes[key] = {"old": before, "new": after}
    return changes
