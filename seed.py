"""
seed.py — Rebuild trump_accounts.db from schema + checked-in seed SQL.

Source of truth for git: schema.sql + *_seed.sql files.
Run after a fresh clone, or any time you want to rebuild from seed state:
    python3 seed.py

Note: zip_income_seed.sql is gitignored (~650KB). If it's not present locally,
run `python3 census_import.py` to repopulate the zip_income table from Census.
"""

import sqlite3
from pathlib import Path

ROOT     = Path(__file__).parent
DB_PATH  = ROOT / "trump_accounts.db"
SCHEMA   = ROOT / "schema.sql"
SEEDS    = ["employers_seed.sql", "state_grants_seed.sql", "zip_income_seed.sql"]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript(SCHEMA.read_text())

    for name in SEEDS:
        path = ROOT / name
        if not path.exists():
            print(f"  {name} not present — skipping (regenerate via export.py or census_import.py)")
            continue
        conn.executescript(path.read_text())
        print(f"✓ replayed {name}")

    conn.commit()

    for table in ("employers", "state_grants", "zip_income"):
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n:,} rows")
        except sqlite3.OperationalError:
            pass

    conn.close()
    print(f"✓ {DB_PATH.name} ready at {DB_PATH}")


if __name__ == "__main__":
    main()
