"""
export.py — Export trump_accounts.db tables to JS files for the frontend.
Run after any DB update:  python3 export.py

Outputs:
  employers.js        — employer seed grant data
  zip_income.js       — ZIP code median income lookup (requires census_import.py first)
  state_grants.js     — state program data (government-funded)
  philanthropic_gifts.js — philanthropic / donor gift data
  state_grants.csv    — flat CSV consumed by Datawrapper state map
  *_seed.sql          — re-seedable SQL dumps for each table
"""

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

DB_PATH = Path(__file__).parent / "trump_accounts.db"

# Public allowlist — every column listed here ships to the public browser via
# .js and to git via *_seed.sql. The guard below (`assert_no_unknown_columns`)
# refuses to run if the DB has any column on `employers` / `state_grants` that
# is NOT in these lists, so a future ALTER TABLE can't silently leak.
# Order matters: it controls SELECT order and INSERT column order in seed SQL.
PUBLIC_EMPLOYER_COLUMNS = [
    "id", "name", "grant_amount", "condition_type", "group_label", "note",
    "sort_order", "contribution_type", "source_url", "verified", "announcement_date",
]

PUBLIC_STATE_GRANT_COLUMNS = [
    "id", "state_code", "grantor_name", "donor_line", "grant_amount", "amount_display",
    "req_no_seed", "req_has_seed", "req_age_max",
    "req_born_year_min", "req_born_year_max",
    "req_zip_income", "income_cap", "req_zip_set", "req_checkbox_labels",
    "note", "source_url", "sort_order", "status",
]

PUBLIC_PHILANTHROPY_COLUMNS = [
    "id", "grantor_name", "donor_line", "donor_type", "total_committed",
    "state_code", "geo_scope", "grant_amount", "amount_display",
    "req_no_seed", "req_has_seed", "req_age_max",
    "req_born_year_min", "req_born_year_max",
    "req_zip_income", "income_cap", "req_zip_set", "req_checkbox_labels",
    "note", "source_url", "sort_order", "is_open_to_apply",
]


def assert_no_unknown_columns(conn, table, allowed):
    """Refuse to run if `table` has columns not on the public allowlist.

    Everything in employers/state_grants ships publicly. Any new column must
    be an explicit, public-aware decision — add it here, or move it to a
    separate table that export.py never touches.
    """
    actual = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    unexpected = actual - set(allowed)
    if unexpected:
        list_name = {
            "employers": "PUBLIC_EMPLOYER_COLUMNS",
            "state_grants": "PUBLIC_STATE_GRANT_COLUMNS",
            "philanthropic_gifts": "PUBLIC_PHILANTHROPY_COLUMNS",
        }.get(table, "the public column allowlist")
        raise SystemExit(
            f"\nexport.py refused to run.\n"
            f"  Table '{table}' has columns NOT in the public allowlist:\n"
            f"    {sorted(unexpected)}\n"
            f"  Every column in '{table}' ships to public .js and .sql.\n"
            f"  Either:\n"
            f"    1) Add the column to {list_name} in export.py (it will become PUBLIC), or\n"
            f"    2) Move it to a separate, non-exported table.\n"
        )


def sql_value(v):
    """Format a Python value as a SQL literal: None→NULL, int/float→bare, str→quoted."""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def export_employers(conn, timestamp):
    cols = ", ".join(PUBLIC_EMPLOYER_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM employers ORDER BY sort_order, name"
    ).fetchall()

    employers = []
    for r in rows:
        amt = r["grant_amount"] if r["grant_amount"] is not None else 0
        entry = {
            "group": r["group_label"],
            "label": r["name"],
            "value": f"{r['id']}|{amt}|{r['condition_type']}|{r['contribution_type']}",
        }
        if r["note"]:
            entry["note"] = r["note"]
        if r["source_url"]:
            entry["source_url"] = r["source_url"]
        if r["verified"]:
            entry["verified"] = True
        entry["sort_order"] = r["sort_order"] if r["sort_order"] is not None else 0
        if r["announcement_date"]:
            entry["announcement_date"] = r["announcement_date"]
        employers.append(entry)

    js = (
        f"// Auto-generated by export.py — do not edit directly.\n"
        f"// Last updated: {timestamp}\n"
        f"const EMPLOYER_DATA = {json.dumps(employers, indent=2, ensure_ascii=False)};\n"
    )
    out = Path(__file__).parent / "employers.js"
    out.write_text(js, encoding="utf-8")
    print(f"✓ employers.js written ({len(employers)} employers)")


def export_zip_income(conn, timestamp):
    # Check if table exists
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zip_income'"
    ).fetchone()

    if not exists:
        print("  zip_income table not found — run `python3 census_import.py` first, skipping.")
        return

    rows = conn.execute(
        "SELECT zip, median_income FROM zip_income WHERE median_income IS NOT NULL"
    ).fetchall()

    # Simple dict: {"10001": 75000, ...} for O(1) frontend lookup
    zip_dict = {r["zip"]: r["median_income"] for r in rows}

    # Pull vintage year from DB
    year_row = conn.execute("SELECT year FROM zip_income WHERE year IS NOT NULL LIMIT 1").fetchone()
    vintage_year = year_row["year"] if year_row else "unknown"

    meta = {
        "source": "U.S. Census Bureau",
        "survey": "American Community Survey (ACS) 5-Year Estimates",
        "table": "B19013 — Median Household Income in the Past 12 Months",
        "vintage_year": vintage_year,
        "exported": timestamp,
    }

    js = (
        f"// Auto-generated by export.py — do not edit directly.\n"
        f"// Last updated: {timestamp}\n"
        f"const ZIP_INCOME_META = {json.dumps(meta, indent=2)};\n"
        f"const ZIP_INCOME = {json.dumps(zip_dict, separators=(',', ':'))};\n"
    )
    out = Path(__file__).parent / "zip_income.js"
    out.write_text(js, encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"✓ zip_income.js written ({len(zip_dict):,} ZIPs, {size_kb:.0f} KB)")


def export_state_grants(conn, timestamp):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='state_grants'"
    ).fetchone()
    if not exists:
        print("  state_grants table not found — skipping.")
        return

    cols = ", ".join(PUBLIC_STATE_GRANT_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM state_grants ORDER BY sort_order, grantor_name"
    ).fetchall()

    grants = [dict(r) for r in rows]
    js = (
        f"// Auto-generated by export.py — do not edit directly.\n"
        f"// Last updated: {timestamp}\n"
        f"const STATE_GRANTS = {json.dumps(grants, indent=2, ensure_ascii=False)};\n"
    )
    out = Path(__file__).parent / "state_grants.js"
    out.write_text(js, encoding="utf-8")
    print(f"✓ state_grants.js written ({len(grants)} grants)")


def export_philanthropy(conn, timestamp):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='philanthropic_gifts'"
    ).fetchone()
    if not exists:
        print("  philanthropic_gifts table not found — skipping.")
        return

    cols = ", ".join(PUBLIC_PHILANTHROPY_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM philanthropic_gifts ORDER BY sort_order, grantor_name"
    ).fetchall()

    gifts = [dict(r) for r in rows]
    js = (
        f"// Auto-generated by export.py — do not edit directly.\n"
        f"// Last updated: {timestamp}\n"
        f"const PHILANTHROPIC_GIFTS = {json.dumps(gifts, indent=2, ensure_ascii=False)};\n"
    )
    out = Path(__file__).parent / "philanthropic_gifts.js"
    out.write_text(js, encoding="utf-8")
    print(f"✓ philanthropic_gifts.js written ({len(gifts)} gifts)")


def export_philanthropy_sql(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='philanthropic_gifts'"
    ).fetchone()
    if not exists:
        print("  philanthropic_gifts table not found — skipping philanthropic_gifts_seed.sql.")
        return

    cols = ", ".join(PUBLIC_PHILANTHROPY_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM philanthropic_gifts ORDER BY sort_order, grantor_name"
    ).fetchall()

    col_list = ",".join(PUBLIC_PHILANTHROPY_COLUMNS)
    lines = ["DELETE FROM philanthropic_gifts;"]
    for r in rows:
        vals = ",".join(sql_value(r[c]) for c in PUBLIC_PHILANTHROPY_COLUMNS)
        lines.append(f"INSERT INTO philanthropic_gifts ({col_list}) VALUES ({vals});")
    Path("philanthropic_gifts_seed.sql").write_text("\n".join(lines))
    print(f"✓ philanthropic_gifts_seed.sql written ({len(rows)} gifts)")


def export_state_grants_csv(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='state_grants'"
    ).fetchone()
    if not exists:
        print("  state_grants table not found — skipping state_grants.csv.")
        return

    has_phil = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='philanthropic_gifts'"
    ).fetchone()
    phil_union = (
        """ UNION ALL
            SELECT state_code, grantor_name, grant_amount, amount_display, note, sort_order
            FROM philanthropic_gifts WHERE state_code IS NOT NULL AND is_open_to_apply = 1"""
        if has_phil else ""
    )
    rows = conn.execute(
        f"""SELECT state_code, grantor_name, grant_amount, amount_display, note, sort_order
            FROM state_grants WHERE state_code IS NOT NULL AND status = 'active'
            {phil_union}
            ORDER BY state_code, sort_order"""
    ).fetchall()

    by_state = {}
    for r in rows:
        by_state.setdefault(r["state_code"], []).append(r)

    def fmt_amount(r):
        if r["amount_display"]:
            return r["amount_display"]
        if r["grant_amount"] is not None:
            return f"${r['grant_amount']:,}"
        return "TBD"

    def short(text, limit=90):
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        cut = text[:limit]
        # back up to last space so we don't cut mid-word
        sp = cut.rfind(" ")
        if sp > 40:
            cut = cut[:sp]
        return cut.rstrip(",;:.-") + "…"

    out_rows = []
    for code in sorted(STATE_NAMES):
        grants = by_state.get(code, [])
        name = STATE_NAMES[code]
        if grants:
            top = grants[0]
            amount = fmt_amount(top)
            elig = (top["note"] or "").strip()
            tooltip = f"<b>{top['grantor_name']}</b> — {amount}<br><small>{short(elig)}</small>"
            out_rows.append([
                code, name, "Yes", len(grants),
                top["grantor_name"], amount, elig, tooltip
            ])
        else:
            tooltip = "No state program announced yet."
            out_rows.append([code, name, "No", 0, "", "", "", tooltip])

    with open("state_grants.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["State Code", "State", "Has Program", "Program Count",
                    "Top Program", "Amount", "Eligibility", "Tooltip"])
        w.writerows(out_rows)

    n_has = sum(1 for r in out_rows if r[2] == "Yes")
    print(f"✓ state_grants.csv written (51 rows, {n_has} with programs)")


def export_state_grants_sql(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='state_grants'"
    ).fetchone()
    if not exists:
        print("  state_grants table not found — skipping state_grants_seed.sql.")
        return

    cols = ", ".join(PUBLIC_STATE_GRANT_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM state_grants ORDER BY sort_order, grantor_name"
    ).fetchall()

    col_list = ",".join(PUBLIC_STATE_GRANT_COLUMNS)
    lines = ["DELETE FROM state_grants;"]
    for r in rows:
        vals = ",".join(sql_value(r[c]) for c in PUBLIC_STATE_GRANT_COLUMNS)
        lines.append(f"INSERT INTO state_grants ({col_list}) VALUES ({vals});")
    Path("state_grants_seed.sql").write_text("\n".join(lines))
    print(f"✓ state_grants_seed.sql written ({len(rows)} grants)")


def sql_quote(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def export_employers_sql(conn):
    cols = ", ".join(PUBLIC_EMPLOYER_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols} FROM employers ORDER BY sort_order, name"
    ).fetchall()

    col_list = ",".join(PUBLIC_EMPLOYER_COLUMNS)
    lines = ["DELETE FROM employers;"]
    for r in rows:
        vals = ",".join(sql_value(r[c]) for c in PUBLIC_EMPLOYER_COLUMNS)
        lines.append(f"INSERT INTO employers ({col_list}) VALUES ({vals});")
    Path("employers_seed.sql").write_text("\n".join(lines))
    print(f"✓ employers_seed.sql written ({len(rows)} employers)")


def export_zip_income_sql(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zip_income'"
    ).fetchone()
    if not exists:
        print("  zip_income table not found — skipping zip_income_seed.sql.")
        return
    rows = conn.execute(
        "SELECT zip, median_income, year FROM zip_income WHERE median_income IS NOT NULL"
    ).fetchall()
    lines = ["DELETE FROM zip_income;"]
    for i in range(0, len(rows), 500):
        chunk = rows[i:i + 500]
        vals = ",".join(
            f"({sql_quote(r['zip'])},{r['median_income']},{r['year']})" for r in chunk
        )
        lines.append(f"INSERT INTO zip_income (zip,median_income,year) VALUES {vals};")
    Path("zip_income_seed.sql").write_text("\n".join(lines))
    size_kb = Path("zip_income_seed.sql").stat().st_size / 1024
    print(f"✓ zip_income_seed.sql written ({len(rows):,} ZIPs, {size_kb:.0f} KB)")


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("trump_accounts.db not found. Run `python3 seed.py` first.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Guard: refuse to publish if the DB has columns we haven't explicitly approved as public.
    assert_no_unknown_columns(conn, "employers", PUBLIC_EMPLOYER_COLUMNS)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='state_grants'").fetchone():
        assert_no_unknown_columns(conn, "state_grants", PUBLIC_STATE_GRANT_COLUMNS)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='philanthropic_gifts'").fetchone():
        assert_no_unknown_columns(conn, "philanthropic_gifts", PUBLIC_PHILANTHROPY_COLUMNS)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    export_employers(conn, timestamp)
    export_zip_income(conn, timestamp)
    export_state_grants(conn, timestamp)
    export_philanthropy(conn, timestamp)
    export_state_grants_csv(conn)
    export_employers_sql(conn)
    export_zip_income_sql(conn)
    export_state_grants_sql(conn)
    export_philanthropy_sql(conn)

    conn.close()


if __name__ == "__main__":
    main()
