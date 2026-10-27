import httpx

url = "https://data.transportation.gov/resource/nakq-58th.json"

try:
    response = httpx.get(
        url,
        params={"$limit": 1},
        timeout=30,
    )
    print("HTTP:", response.status_code)
    print("URL:", response.url)
    print("Response:", response.text[:500])
    response.raise_for_status()

    data = response.json()
    print("Rows:", len(data))
    print("Fields:", sorted(data[0].keys()) if data else "No records returned")

except Exception as exc:
    print(type(exc).__name__ + ":", exc)
