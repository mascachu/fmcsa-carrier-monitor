import httpx
from app.normalize import normalized_row, row_identifiers

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
            r = client.get(
                f"https://data.transportation.gov/resource/{dataset_id}.json",
                params={"$limit": 1},
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                print(f"{name}: NO SAMPLE")
                continue
            row = normalized_row(rows[0])
            usdot, docket, record_key = row_identifiers(name, row)
            print(
                f"{name}: OK | USDOT={usdot} | MC={docket} "
                f"| record_key_created={bool(record_key)}"
            )
        except Exception as e:
            print(f"{name}: ERROR | {type(e).__name__}: {e}")
