from __future__ import annotations
import httpx
from typing import Any

# Verified daily-difference dataset IDs listed by FMCSA's Open Data Program.
# Dataset schemas should always be checked against the current data dictionary.
FMCSA_DAILY_DATASETS = {
    "motus_carrier": "nakq-58th",
    "motus_inshist": "xe5s-wca7",
    "motus_authhist": "dm5j-zc6c",
    "motus_insur": "x96h-evps",
    "motus_revokesuspend": "e67p-xyd5",
}
BASE_URL = "https://data.transportation.gov/resource"

class FMCSAClient:
    def __init__(self, app_token: str = "", page_size: int = 50000, timeout: float = 60.0):
        self.app_token = app_token
        self.page_size = min(max(page_size, 1), 50000)
        self.timeout = timeout

    def fetch_dataset(self, dataset_id: str) -> list[dict[str, Any]]:
        headers = {"Accept": "application/json", "User-Agent": "FMCSA-Change-Monitor-Portfolio/0.1"}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        results: list[dict[str, Any]] = []
        offset = 0
        with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            while True:
                response = client.get(
                    f"{BASE_URL}/{dataset_id}.json",
                    params={"$limit": self.page_size, "$offset": offset, "$order": ":id"},
                )
                response.raise_for_status()
                page = response.json()
                if not isinstance(page, list):
                    raise ValueError(f"Unexpected FMCSA response for dataset {dataset_id}: expected JSON list")
                results.extend(page)
                if len(page) < self.page_size:
                    break
                offset += len(page)
        return results

    def fetch_daily_datasets(self) -> dict[str, list[dict[str, Any]]]:
        return {name: self.fetch_dataset(dataset_id) for name, dataset_id in FMCSA_DAILY_DATASETS.items()}
