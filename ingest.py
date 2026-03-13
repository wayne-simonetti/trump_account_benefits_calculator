"""
ingest.py — Extract Trump Account grant data from text and load into trump_accounts.db.

Handles two grant types:
  employer  — company seed grants / employer matches  → employers table
  grant     — state / philanthropic grants            → state_grants table

Auto-detects type from text, or use --type to force.

Usage:
  python3 ingest.py                         # interactive paste
  python3 ingest.py tweets.txt              # file (blank-line separated blocks)
  python3 ingest.py --type employer         # force employer mode
  python3 ingest.py --type grant            # force state/philanthropic mode

Setup:
  pip3 install anthropic
  export ANTHROPIC_API_KEY=your_key_here
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run:  pip3 install anthropic")
    sys.exit(1)

DB_PATH = Path(__file__).parent / "trump_accounts.db"

# ── Prompts ────────────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are classifying text about Trump Account (child savings account) grants.
Respond with exactly one word: "employer", "grant", or "both".

employer — a company/employer announcing a seed grant or match for employees' children
grant    — a state government, nonprofit, or philanthropist announcing a grant for eligible children
both     — text mentions both

Return ONLY the single word."""

EMPLOYER_PROMPT = """You are a structured data extraction assistant. Extract employer matching / seed grant
information for Trump Accounts from the provided text.

Return a JSON array. Each element = one employer grant. Empty array [] if none found.

Each object must have exactly these fields:
{
  "employer_name": "string — official company name",
  "grant_amount": integer or null,
  "condition_type": "all" | "seed" | "newborn" | "conditional" | "variable",
  "contribution_type": "seed_grant" | "employer_match",
  "note": "string or null",
  "source_url": "string or null — URL to announcement if present in text",
  "confidence": "high" | "medium" | "low"
}

condition_type:
  all         — all eligible children of US employees
  seed        — only children born Jan 1 2025–Dec 31 2028
  newborn     — only newborns / recently born
  conditional — base amount plus conditional requirement
  variable    — amount not yet specified

contribution_type:
  seed_grant     — one-time employer deposit; exempt from $5,000 annual cap
  employer_match — recurring annual contribution (up to $2,500/yr, within $5,000 cap)

Return ONLY valid JSON."""

GRANT_PROMPT = """You are a structured data extraction assistant. Extract state government or philanthropic
grant information for Trump Accounts (child savings accounts) from the provided text.

Return a JSON array. Each element = one grant program. Empty array [] if none found.

Each object must have exactly these fields:
{
  "grantor_name": "string — official name of the granting org or program",
  "donor_line": "string or null — short attribution, e.g. 'Ray & Barbara Dalio — $75M commitment'",
  "state_code": "string or null — 2-letter state abbreviation; null if nationwide",
  "grant_amount": integer or null,
  "amount_display": "string or null — e.g. '~$500' or 'TBD' if exact amount unclear",
  "req_no_seed": 0 or 1,
  "req_has_seed": 0 or 1,
  "req_age_max": integer or null,
  "req_born_year": integer or null,
  "req_zip_income": 0 or 1,
  "income_cap": integer or null,
  "note": "string or null — key eligibility caveat",
  "source_url": "string or null — URL to announcement if present in text",
  "confidence": "high" | "medium" | "low"
}

req_no_seed   — 1 if child must NOT have the $1,000 federal seed deposit
req_has_seed  — 1 if child MUST have the federal seed deposit
req_age_max   — max age (inclusive) if there is an age cap, else null
req_born_year — exact birth year required (e.g. 2025), else null
req_zip_income — 1 if eligibility depends on ZIP median income being below a threshold
income_cap    — the income threshold in dollars when req_zip_income=1

Return ONLY valid JSON."""

# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[''']", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:40]


def call_claude(system: str, user: str, max_tokens: int = 1024) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def classify(text: str) -> str:
    result = call_claude(CLASSIFY_PROMPT, text, max_tokens=10).lower()
    for t in ("employer", "grant", "both"):
        if t in result:
            return t
    return "employer"  # safe default


# ── Employer ingestion ─────────────────────────────────────────────────────────

def employer_group_label(amount, condition_type):
    if condition_type == "variable" or amount is None:
        return "Variable — contact HR"
    if condition_type == "conditional":
        return f"${amount:,} + conditional grant"
    return f"${amount:,} one-time grant"


def next_sort(conn, table: str) -> int:
    row = conn.execute(f"SELECT MAX(sort_order) FROM {table}").fetchone()
    return (row[0] or 0) + 10


def existing_ids(conn, table: str) -> dict:
    rows = conn.execute(f"SELECT id, {'name' if table == 'employers' else 'grantor_name'} FROM {table}").fetchall()
    return {r[0]: r[1] for r in rows}


def print_employer(r: dict):
    print(f"  Employer   : {r['employer_name']}")
    print(f"  Amount     : {'Variable' if r['grant_amount'] is None else '$' + str(r['grant_amount'])}")
    print(f"  Condition  : {r['condition_type']}")
    print(f"  Contrib    : {r.get('contribution_type', 'seed_grant')}")
    print(f"  Note       : {r.get('note') or '—'}")
    print(f"  Source URL : {r.get('source_url') or '—'}")
    print(f"  Confidence : {r['confidence']}")


def write_employer(conn, r: dict, sort_order: int) -> str:
    eid = slugify(r["employer_name"])
    conn.execute(
        """INSERT OR REPLACE INTO employers
           (id, name, grant_amount, condition_type, group_label, note, sort_order, contribution_type, source_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            eid,
            r["employer_name"],
            r["grant_amount"],
            r["condition_type"],
            employer_group_label(r["grant_amount"], r["condition_type"]),
            r.get("note"),
            sort_order,
            r.get("contribution_type", "seed_grant"),
            r.get("source_url"),
        ),
    )
    return eid


def ingest_employers(text: str, conn):
    raw = call_claude(EMPLOYER_PROMPT, f"Extract employer grant data:\n\n{text}")
    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ✗ Claude returned non-JSON: {e}")
        return

    if not results:
        print("  No employer grant data found.")
        return

    existing = existing_ids(conn, "employers")
    sort_order = next_sort(conn, "employers")

    for r in results:
        print()
        print_employer(r)
        eid = slugify(r["employer_name"])
        if eid in existing:
            print(f"  ⚠ Already in DB as '{existing[eid]}' (id: {eid})")
            if input("  Update existing? [y/N] ").strip().lower() != "y":
                print("  Skipped.")
                continue
        else:
            if input("  Add to DB? [y/N] ").strip().lower() != "y":
                print("  Skipped.")
                continue
        write_employer(conn, r, sort_order)
        conn.commit()
        sort_order += 10
        print(f"  ✓ Written (id: {eid})")


# ── State/philanthropic grant ingestion ───────────────────────────────────────

def print_grant(r: dict):
    print(f"  Grantor    : {r['grantor_name']}")
    print(f"  Donor line : {r.get('donor_line') or '—'}")
    print(f"  State      : {r.get('state_code') or 'Nationwide'}")
    amt = r.get('grant_amount')
    disp = r.get('amount_display')
    print(f"  Amount     : {disp or ('$' + str(amt) if amt else 'TBD')}")
    flags = []
    if r.get('req_no_seed'):  flags.append('no federal seed')
    if r.get('req_has_seed'): flags.append('must have federal seed')
    if r.get('req_age_max'):  flags.append(f'age ≤ {r["req_age_max"]}')
    if r.get('req_born_year'): flags.append(f'born {r["req_born_year"]}')
    if r.get('req_zip_income'): flags.append(f'ZIP income < ${r.get("income_cap", "?"):,}' if r.get('income_cap') else 'ZIP income cap')
    print(f"  Eligibility: {', '.join(flags) or 'none specified'}")
    print(f"  Note       : {r.get('note') or '—'}")
    print(f"  Source URL : {r.get('source_url') or '—'}")
    print(f"  Confidence : {r['confidence']}")


def write_grant(conn, r: dict, sort_order: int) -> str:
    gid = slugify(r["grantor_name"])
    conn.execute(
        """INSERT OR REPLACE INTO state_grants
           (id, state_code, grantor_name, donor_line, grant_amount, amount_display,
            req_no_seed, req_has_seed, req_age_max, req_born_year,
            req_zip_income, income_cap, note, source_url, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            gid,
            r.get("state_code"),
            r["grantor_name"],
            r.get("donor_line"),
            r.get("grant_amount"),
            r.get("amount_display"),
            int(r.get("req_no_seed") or 0),
            int(r.get("req_has_seed") or 0),
            r.get("req_age_max"),
            r.get("req_born_year"),
            int(r.get("req_zip_income") or 0),
            r.get("income_cap"),
            r.get("note"),
            r.get("source_url"),
            sort_order,
        ),
    )
    return gid


def ingest_grants(text: str, conn):
    raw = call_claude(GRANT_PROMPT, f"Extract state/philanthropic grant data:\n\n{text}")
    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ✗ Claude returned non-JSON: {e}")
        return

    if not results:
        print("  No state/philanthropic grant data found.")
        return

    existing = existing_ids(conn, "state_grants")
    sort_order = next_sort(conn, "state_grants")

    for r in results:
        print()
        print_grant(r)
        gid = slugify(r["grantor_name"])
        if gid in existing:
            print(f"  ⚠ Already in DB as '{existing[gid]}' (id: {gid})")
            if input("  Update existing? [y/N] ").strip().lower() != "y":
                print("  Skipped.")
                continue
        else:
            if input("  Add to DB? [y/N] ").strip().lower() != "y":
                print("  Skipped.")
                continue
        write_grant(conn, r, sort_order)
        conn.commit()
        sort_order += 10
        print(f"  ✓ Written (id: {gid})")


# ── Text processing ────────────────────────────────────────────────────────────

def process_text(text: str, conn, force_type: str = None):
    text = text.strip()
    if not text:
        return

    print(f"\n─── Analyzing ({'...' + text[-60:] if len(text) > 80 else text}) ───")

    grant_type = force_type or classify(text)
    print(f"  Type: {grant_type}")

    try:
        if grant_type in ("employer", "both"):
            ingest_employers(text, conn)
        if grant_type in ("grant", "both"):
            ingest_grants(text, conn)
    except anthropic.APIError as e:
        print(f"  ✗ API error: {e}")
        return

    print(f"\nDone. Run `python3 export.py` to push changes to the frontend.")


def read_blocks(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in re.split(r"\n{2,}", content)]
    return [b for b in blocks if b]


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    if not DB_PATH.exists():
        print("trump_accounts.db not found. Run `python3 seed.py` first.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set your API key:  export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    args = sys.argv[1:]
    force_type = None
    file_arg = None

    i = 0
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            force_type = args[i + 1]
            if force_type not in ("employer", "grant", "both"):
                print("--type must be employer, grant, or both")
                sys.exit(1)
            i += 2
        else:
            file_arg = args[i]
            i += 1

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    if file_arg:
        path = Path(file_arg)
        if not path.exists():
            print(f"File not found: {path}")
            sys.exit(1)
        blocks = read_blocks(path)
        print(f"Found {len(blocks)} block(s) in {path}")
        for block in blocks:
            process_text(block, conn, force_type)
    else:
        print("Paste text below. Press Enter twice (blank line) when done.")
        print("Type 'quit' to exit.\n")
        while True:
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line.lower() == "quit":
                    conn.close()
                    sys.exit(0)
                if line == "" and lines:
                    break
                lines.append(line)
            if not lines:
                continue
            process_text("\n".join(lines), conn, force_type)
            print("\nPaste another block, or type 'quit' to exit.\n")

    conn.close()


if __name__ == "__main__":
    main()
