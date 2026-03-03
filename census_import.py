"""
census_import.py — Download ACS median household income by ZIP (ZCTA) from
the Census Bureau and load it into the zip_income table in trump_accounts.db.

Source: ACS 5-year estimates, Table B19013 (Median Household Income)
Run once per year when new ACS data is released:  python3 census_import.py

No API key required for this request.
"""

import json
import sqlite3
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent / "trump_accounts.db"

ACS_YEAR = 2024
CENSUS_URL = (
    f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
    f"?get=B19013_001E,NAME"
    f"&for=zip%20code%20tabulation%20area:*"
)


def fetch_data():
    print(f"Fetching ACS {ACS_YEAR} 5-year median income data from Census Bureau...")
    print(f"  {CENSUS_URL}\n")
    req = urllib.request.Request(CENSUS_URL, headers={"User-Agent": "trump-account-tool/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def load(data):
    headers   = data[0]
    income_col = headers.index("B19013_001E")
    zcta_col   = headers.index("zip code tabulation area")

    records = []
    skipped = 0
    for row in data[1:]:
        zcta = row[zcta_col]
        raw  = row[income_col]
        # Census uses -666666666 for suppressed/unavailable values
        try:
            income = int(raw)
            income = income if income > 0 else None
        except (TypeError, ValueError):
            income = None

        if income is None:
            skipped += 1

        records.append((zcta, income, ACS_YEAR))

    return records, skipped


def write_db(records):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS zip_income (
            zip           TEXT    PRIMARY KEY,
            median_income INTEGER,
            year          INTEGER
        )
    """)
    conn.executemany(
        "INSERT OR REPLACE INTO zip_income (zip, median_income, year) VALUES (?, ?, ?)",
        records,
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM zip_income WHERE median_income IS NOT NULL").fetchone()[0]
    conn.close()
    return count


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("trump_accounts.db not found. Run `python3 seed.py` first.")

    data           = fetch_data()
    records, skipped = load(data)
    count          = write_db(records)

    print(f"✓ {len(records):,} ZCTA records processed")
    print(f"  {count:,} with valid income data written to zip_income")
    print(f"  {skipped:,} suppressed/unavailable (stored as NULL)")
    print(f"\nRun `python3 export.py` to regenerate zip_income.js")


if __name__ == "__main__":
    main()
