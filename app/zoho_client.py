from __future__ import annotations
from datetime import date, timedelta
import httpx
from typing import Any
from .config import settings

class ZohoClient:
    """Optional idempotent alert upsert to a custom Zoho CRM module.

    Prerequisite: create a custom module and mark Event_Key as unique. Confirm every
    custom-field API name in the target Zoho org before enabling this integration.
    """
    def __init__(self) -> None:
        required = [settings.zoho_accounts_url, settings.zoho_api_base,
                    settings.zoho_client_id, settings.zoho_client_secret, settings.zoho_refresh_token]
        if not all(required):
            raise RuntimeError("Zoho sync enabled, but OAuth settings are incomplete")
        self._cached_access_token: str | None = None

    def access_token(self, force_refresh: bool = False) -> str:
        if self._cached_access_token and not force_refresh:
            return self._cached_access_token
        response = httpx.post(
            f"{settings.zoho_accounts_url.rstrip('/')}/oauth/v2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.zoho_client_id,
                "client_secret": settings.zoho_client_secret,
                "refresh_token": settings.zoho_refresh_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        token = body.get("access_token")
        if not token:
            raise RuntimeError(f"Zoho OAuth did not return access_token: {body.get('error', 'unknown error')}")
        self._cached_access_token = token
        return token

    def _upsert(self, module_api_name: str, key_field: str, record: dict[str, Any]) -> dict[str, Any]:
        token = self.access_token()
        body = {"data": [record], "duplicate_check_fields": [key_field]}
        response = httpx.put(
            f"{settings.zoho_api_base.rstrip('/')}/crm/v8/{module_api_name}/upsert",
            headers={"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        if response.status_code == 401:
            token = self.access_token(force_refresh=True)
            response = httpx.put(
                f"{settings.zoho_api_base.rstrip('/')}/crm/v8/{module_api_name}/upsert",
                headers={"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"},
                json=body, timeout=30,
            )
        response.raise_for_status()
        result = response.json()
        entries = result.get("data") or []
        if entries and entries[0].get("status") != "success":
            raise RuntimeError(f"Zoho {module_api_name} upsert failed: {entries[0].get('code')}: {entries[0].get('message')}")
        if not entries and result.get("code") not in {None, "SUCCESS"}:
            raise RuntimeError(f"Zoho {module_api_name} upsert failed: {result.get('code')}: {result.get('message')}")
        return result

    def upsert_alert(self, event: dict[str, Any]) -> dict[str, Any]:
        record = {
            "Name": f"{event['event_type']} — USDOT {event.get('usdot_number') or 'unknown'}",
            settings.zoho_event_key_field: event["event_key"],
            "USDOT_Number": event.get("usdot_number"),
            "MC_Number": event.get("mc_number"),
            "Event_Type": event["event_type"],
            "Event_Date": str(event["event_date"]) if event.get("event_date") else None,
            "Description": event["summary"],
            "Severity": event["severity"],
        }
        return self._upsert(settings.zoho_alert_module, settings.zoho_event_key_field, record)

    def upsert_task(self, event: dict[str, Any]) -> dict[str, Any]:
        if not settings.zoho_tasks_enabled:
            raise RuntimeError("Zoho task sync is disabled")
        account_link = None
        if event.get("zoho_account_id"):
            account_link = {"id": event["zoho_account_id"], "module": {"api_name": "Accounts"}}
        record: dict[str, Any] = {
            "Subject": f"Review FMCSA alert: {event['event_type']} — USDOT {event.get('usdot_number') or 'unknown'}",
            settings.zoho_task_event_key_field: f"{event['event_key']}:task",
            "Due_Date": (date.today() + timedelta(days=max(settings.zoho_task_due_days, 0))).isoformat(),
            "Status": "Not Started",
            "Priority": "High" if event.get("severity") == "high" else "Normal",
            "Description": event["summary"],
        }
        if account_link:
            record["What_Id"] = account_link
        return self._upsert("Tasks", settings.zoho_task_event_key_field, record)
