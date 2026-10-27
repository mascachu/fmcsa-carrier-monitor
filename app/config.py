from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://fmcsa_app:change-me@localhost:5432/fmcsa_monitor")
    run_token: str = os.getenv("FMCSA_RUN_TOKEN", "")
    socrata_app_token: str = os.getenv("SOCRATA_APP_TOKEN", "")
    baseline_mode: bool = os.getenv("FMCSA_BASELINE_MODE", "false").lower() == "true"
    zoho_sync_enabled: bool = os.getenv("ZOHO_SYNC_ENABLED", "false").lower() == "true"
    zoho_accounts_url: str = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
    zoho_api_base: str = os.getenv("ZOHO_API_BASE", "https://www.zohoapis.com")
    zoho_client_id: str = os.getenv("ZOHO_CLIENT_ID", "")
    zoho_client_secret: str = os.getenv("ZOHO_CLIENT_SECRET", "")
    zoho_refresh_token: str = os.getenv("ZOHO_REFRESH_TOKEN", "")
    zoho_alert_module: str = os.getenv("ZOHO_ALERT_MODULE_API_NAME", "FMCSA_Alerts")
    zoho_event_key_field: str = os.getenv("ZOHO_EVENT_KEY_FIELD_API_NAME", "Event_Key")
    zoho_tasks_enabled: bool = os.getenv("ZOHO_TASKS_ENABLED", "false").lower() == "true"
    zoho_task_event_key_field: str = os.getenv("ZOHO_TASK_EVENT_KEY_FIELD_API_NAME", "FMCSA_Event_Key")
    zoho_task_due_days: int = int(os.getenv("ZOHO_TASK_DUE_DAYS", "1"))

settings = Settings()
