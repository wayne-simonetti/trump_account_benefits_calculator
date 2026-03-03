"""
tweet_ingest.py — Extract employer grant data from tweet text and load into trump_accounts.db.

Focuses exclusively on company Trump Account matching programs / employer seed grants.
Uses Claude to extract structured data, then prompts for confirmation before writing.

Usage:
  python3 tweet_ingest.py                  # paste tweet text interactively
  python3 tweet_ingest.py tweets.txt       # process a file (one tweet per line or blank-line separated)

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

SYSTEM_PROMPT = """You are a structured data extraction assistant. Your only job is to extract
employer matching / seed grant information for Trump Accounts (child savings accounts created
under the One Big Beautiful Bill Act) from the provided text.

Return a JSON array. Each element represents one distinct employer grant announcement found in
the text. If no employer grant information is present, return an empty array [].

Each object must have exactly these fields:
{
  "employer_name": "string — official company name",
  "grant_amount": integer or null — dollar amount per child (null if not specified or variable),
  "condition_type": "all" | "seed" | "newborn" | "conditional" | "variable",
  "contribution_type": "seed_grant" | "employer_match",
  "note": "string or null — key eligibility condition or caveat",
  "confidence": "high" | "medium" | "low"
}

contribution_type definitions:
  seed_grant     — one-time employer deposit (like the federal $1,000 seed); exempt from $5,000 annual cap
  employer_match — recurring annual employer contribution (up to $2,500/yr, within $5,000 cap)

condition_type definitions:
  all         — available for all eligible children of U.S. employees
  seed        — only for children born January 1 2025 through December 31 2028
  newborn     — only for newborns / recently born children of employees
  conditional — base amount plus additional amount contingent on a requirement
  variable    — amount not yet specified; company has pledged but not published a number

Return ONLY valid JSON. No explanation, no markdown, no other text."""


def build_id(name: str) -> str:
    """Generate a slug ID from employer name."""
    slug = name.lower()
    slug = re.sub(r"[''']", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:40]


def group_label(amount, condition_type):
    if condition_type == "variable" or amount is None:
        return "Variable — contact HR"
    if condition_type == "conditional":
        return f"${amount:,} + conditional grant"
    return f"${amount:,} one-time grant"


def extract(text: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Extract employer grant data from this text:\n\n{text}"}],
    )
    raw = message.content[0].text.strip()
    return json.loads(raw)


def existing_employers(conn) -> dict:
    rows = conn.execute("SELECT id, name FROM employers").fetchall()
    return {r[0]: r[1] for r in rows}


def next_sort_order(conn) -> int:
    row = conn.execute("SELECT MAX(sort_order) FROM employers").fetchone()
    return (row[0] or 0) + 10


def print_record(r: dict):
    print(f"  Employer   : {r['employer_name']}")
    print(f"  Amount     : {'Variable' if r['grant_amount'] is None else '$' + str(r['grant_amount'])}")
    print(f"  Condition  : {r['condition_type']}")
    print(f"  Contrib    : {r.get('contribution_type', 'seed_grant')}")
    print(f"  Note       : {r['note'] or '—'}")
    print(f"  Confidence : {r['confidence']}")


def write_record(conn, r: dict, sort_order: int):
    eid = build_id(r["employer_name"])
    conn.execute(
        """
        INSERT OR REPLACE INTO employers (id, name, grant_amount, condition_type, group_label, note, sort_order, contribution_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eid,
            r["employer_name"],
            r["grant_amount"],
            r["condition_type"],
            group_label(r["grant_amount"], r["condition_type"]),
            r["note"],
            sort_order,
            r.get("contribution_type", "seed_grant"),
        ),
    )
    return eid


def process_text(text: str, conn):
    text = text.strip()
    if not text:
        return

    print(f"\n─── Analyzing text ({'...' + text[-60:] if len(text) > 80 else text}) ───")

    try:
        results = extract(text)
    except json.JSONDecodeError as e:
        print(f"  ✗ Claude returned non-JSON: {e}")
        return
    except anthropic.APIError as e:
        print(f"  ✗ API error: {e}")
        return

    if not results:
        print("  No employer grant data found.")
        return

    existing = existing_employers(conn)
    sort_order = next_sort_order(conn)

    for r in results:
        print()
        print_record(r)

        eid = build_id(r["employer_name"])
        if eid in existing:
            print(f"  ⚠ Already in DB as '{existing[eid]}' (id: {eid})")
            action = input("  Update existing record? [y/N] ").strip().lower()
            if action != "y":
                print("  Skipped.")
                continue
        else:
            action = input("  Add to DB? [y/N] ").strip().lower()
            if action != "y":
                print("  Skipped.")
                continue

        written_id = write_record(conn, r, sort_order)
        conn.commit()
        sort_order += 10
        print(f"  ✓ Written (id: {written_id})")

    print(f"\nDone. Run `python3 export.py` to push changes to the frontend.")


def read_tweets_from_file(path: Path) -> list[str]:
    """Split file into individual tweets on blank lines."""
    content = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in re.split(r"\n{2,}", content)]
    return [b for b in blocks if b]


def main():
    if not DB_PATH.exists():
        print("trump_accounts.db not found. Run `python3 seed.py` first.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set your API key:  export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    if len(sys.argv) > 1:
        # File mode
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"File not found: {path}")
            sys.exit(1)
        tweets = read_tweets_from_file(path)
        print(f"Found {len(tweets)} tweet(s) in {path}")
        for tweet in tweets:
            process_text(tweet, conn)
    else:
        # Interactive mode
        print("Paste tweet text below. Press Enter twice (blank line) when done.")
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
            process_text("\n".join(lines), conn)
            print("\nPaste another tweet, or type 'quit' to exit.\n")

    conn.close()


if __name__ == "__main__":
    main()
