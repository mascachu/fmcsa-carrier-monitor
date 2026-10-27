import httpx

datasets = {
    "motus_carrier": "nakq-58th",
    "motus_inshist": "xe5s-wca7",
    "motus_authhist": "dm5j-zc6c",
    "motus_insur": "x96h-evps",
    "motus_revokesuspend": "e67p-xyd5",
}

with httpx.Client(timeout=25) as client:
    for name, dataset_id in datasets.items():
        try:
            response = client.get(
                f"https://data.transportation.gov/resource/{dataset_id}.json",
                params={"$limit": 1},
            )
            print(f"\n{name}: HTTP {response.status_code}")
            response.raise_for_status()
            rows = response.json()
            print("Sample rows:", len(rows))
            print("Fields:", ", ".join(rows[0].keys()) if rows else "NO SAMPLE ROW")
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
