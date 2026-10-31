
from __future__ import annotations

import time
from typing import Any

import httpx


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

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class FMCSAClient:
    def __init__(
        self,
        app_token: str = "",
        page_size: int = 5000,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.app_token = app_token
        self.page_size = min(max(page_size, 1), 50000)
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

    def _get_with_retry(
        self,
        client: httpx.Client,
        url: str,
        params: dict[str, Any],
        dataset_id: str,
    ) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = client.get(url, params=params)

                if response.status_code not in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response

                if attempt == self.max_retries:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt

                time.sleep(min(max(delay, 1), 30))

            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                time.sleep(min(2**attempt, 30))

        raise RuntimeError(f"Request retries exhausted for dataset {dataset_id}")

    def fetch_dataset(self, dataset_id: str) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "FMCSA-Change-Monitor-Portfolio/0.1",
        }

        if self.app_token:
            headers["X-App-Token"] = self.app_token

        results: list[dict[str, Any]] = []
        offset = 0

        with httpx.Client(
            timeout=self.timeout,
            headers=headers,
            follow_redirects=True,
        ) as client:
            while True:
                response = self._get_with_retry(
                    client=client,
                    url=f"{BASE_URL}/{dataset_id}.json",
                    params={
                        "$limit": self.page_size,
                        "$offset": offset,
                        "$order": ":id",
                    },
                    dataset_id=dataset_id,
                )

                page = response.json()

                if not isinstance(page, list):
                    raise ValueError(
                        f"Unexpected FMCSA response for dataset {dataset_id}: "
                        "expected JSON list"
                    )

                results.extend(page)

                if len(page) < self.page_size:
                    break

                offset += len(page)

        return results

    def fetch_daily_datasets(self) -> dict[str, list[dict[str, Any]]]:
        return {
            name: self.fetch_dataset(dataset_id)
            for name, dataset_id in FMCSA_DAILY_DATASETS.items()
        }
