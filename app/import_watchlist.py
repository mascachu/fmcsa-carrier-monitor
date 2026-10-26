from __future__ import annotations
import csv
import sys
from pathlib import Path
from .repository import initialize_db, import_watchlist

if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/app/data/watchlist.csv")
    initialize_db()
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Imported/updated {import_watchlist(rows)} watched companies from {path}")
