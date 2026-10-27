import httpx
from app.normalize import normalized_row, row_identifiers

DATASETS = {
    "motus_carrier": "nakq-58th",
    "motus_inshist": "xe5s-wca7",
    "motus_authhist": "dm5j-zc6c",
    "motus_insur": "x96h-evps",
    "motus_revokesuspend": "e67p-xyd5",
}

def main():
    passed = 0

    with httpx.Client(timeout=30) as client:
        for name, dataset_id in DATASETS.items():
            response = client.get(
                f"https://data.transportation.gov/resource/{dataset_id}.json",
                params={"$limit": 1},
            )
            response.raise_for_status()

            rows = response.json()
            assert isinstance(rows, list), f"{name}: response is not a list"
            assert rows, f"{name}: no sample record returned"

            row = normalized_row(rows[0])
            usdot, docket, record_key = row_identifiers(name, row)

            assert usdot or docket, f"{name}: missing USDOT and MC"
            assert record_key, f"{name}: missing record key"

            print(
                f"PASS {name}: "
                f"USDOT={usdot}, MC={docket}, key_created=True"
            )
            passed += 1

    print(f"\nRESULT: {passed}/{len(DATASETS)} datasets passed")
    assert passed == len(DATASETS)

if __name__ == "__main__":
    main()
