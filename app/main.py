from __future__ import annotations
from datetime import datetime, timezone
import secrets
from typing import Any
from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .fmcsa_client import FMCSAClient, FMCSA_DAILY_DATASETS
from .repository import (
    initialize_db,
    connect,
    start_run,
    finish_run,
    pending_zoho_events,
    record_zoho_attempt,
    list_runs,
    daily_run_lock,
)
from .processor import process_record
from .reporting import write_daily_report, latest_events

app = FastAPI(title="FMCSA Daily Change Monitor", version="0.1.0", description="Portfolio proof-of-concept for daily FMCSA changes, PostgreSQL history, duplicate-safe events, n8n and optional Zoho CRM alerts.")

@app.on_event("startup")
def startup() -> None:
    initialize_db()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fmcsa-monitor", "version": "0.1.0"}

@app.get("/auth-check")
def auth_check(
    x_run_token: str | None = Header(default=None),
) -> dict[str, str]:
    if (
        not settings.run_token
        or not x_run_token
        or not secrets.compare_digest(settings.run_token, x_run_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Run-Token",
        )

    return {"status": "ok", "authentication": "valid"}

@app.get("/sources")
def sources() -> dict[str, Any]:
    return {"daily_difference_sources": FMCSA_DAILY_DATASETS, "note": "Confirm current source schemas and data dictionaries before production use."}

@app.get("/events")
def events(limit: int = 50) -> list[dict[str, Any]]:
    return latest_events(min(max(limit, 1), 500))

@app.get("/runs")
def runs(limit: int = 50) -> list[dict[str, Any]]:
    return list_runs(limit)

@app.post("/run/daily")


def run_daily(x_run_token: str | None = Header(default=None)) -> dict[str, Any]:
    if (
        not settings.run_token
        or not x_run_token
        or not secrets.compare_digest(settings.run_token, x_run_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Run-Token",
        )

    with daily_run_lock() as acquired:
        if not acquired:
            raise HTTPException(
                status_code=409,
                detail="A daily run is already in progress",
            )

        run_key = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_id = start_run(run_key)

        source_counts: dict[str, int] = {}
        errors: list[str] = []
        rows_matched = 0
        events_created = 0
        report_path = None
        status = "running"

        try:
            feeds = FMCSAClient(
                settings.socrata_app_token
            ).fetch_daily_datasets()

            with connect() as conn:
                for source_name, rows in feeds.items():
                    source_counts[source_name] = len(rows)

                    for raw in rows:
                        try:
                            result = process_record(conn, source_name, raw)
                            rows_matched += result["matched_companies"]
                            events_created += result["events_created"]
                        except Exception as exc:
                            errors.append(
                                f"{source_name}: row processing failed: "
                                f"{type(exc).__name__}: {exc}"
                            )

            if settings.zoho_sync_enabled:
                from .zoho_client import ZohoClient

                zoho = ZohoClient()
                for event in pending_zoho_events():
                    try:
                        response = zoho.upsert_alert(event)
                        record_zoho_attempt(
                            event["id"], "sent", f"alert upsert: {response}"
                        )

                        if (
                            settings.zoho_tasks_enabled
                            and event.get("severity") == "high"
                        ):
                            task_response = zoho.upsert_task(event)
                            record_zoho_attempt(
                                event["id"],
                                "sent",
                                f"task upsert: {task_response}",
                            )
                    except Exception as exc:
                        record_zoho_attempt(
                            event["id"],
                            "failed",
                            f"{type(exc).__name__}: {exc}",
                        )
                        errors.append(
                            f"Zoho delivery failed for event {event['id']}: "
                            f"{type(exc).__name__}: {exc}"
                        )

            status = "completed_with_errors" if errors else "completed"

        except Exception as exc:
            errors.append(
                f"FMCSA ingestion failed: {type(exc).__name__}: {exc}"
            )
            status = "failed"

        try:
            report_path = write_daily_report(
                run_id,
                run_key,
                status,
                source_counts,
                rows_matched,
                events_created,
                errors,
            )
        except Exception as exc:
            errors.append(
                f"Report generation failed: {type(exc).__name__}: {exc}"
            )
            status = "failed"

        try:
            finish_run(
                run_id,
                status,
                source_counts,
                rows_matched,
                events_created,
                errors,
                report_path,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Failed to save daily run status",
            ) from exc

        return {
            "run_id": run_id,
            "run_key": run_key,
            "status": status,
            "source_counts": source_counts,
            "rows_matched_to_watchlist": rows_matched,
            "new_events_created": events_created,
            "errors_count": len(errors),
            "report_path": report_path,
            "zoho_sync_enabled": settings.zoho_sync_enabled,
        }
