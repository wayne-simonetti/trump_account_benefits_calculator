"""
atr_check.py — Daily diff: ATR page vs local employers DB.

Fetches https://atr.org/trumpaccounts/, parses employer/contributor names from
<strong> tags in the page body, and reports any not yet in trump_accounts.db.

Appends results to atr_check.log.
Exits 0 if no new employers found; exits 1 if new employers found.

Usage:
  python3 atr_check.py
"""

import gzip
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ATR_URL = "https://atr.org/trumpaccounts/"
DB_PATH = Path(__file__).parent / "trump_accounts.db"
LOG_PATH = Path(__file__).parent / "atr_check.log"

def normalize(name):
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


class ATRParser(HTMLParser):
    """Parse employer/contributor names from ATR page <strong> tags."""

    def __init__(self):
        super().__init__()
        self.employers = []
        self._in_strong = False
        self._current = ""

    SKIP_NAMES = {"company", "organization", "employer", "name", ""}

    def handle_starttag(self, tag, attrs):
        if tag == "strong":
            self._in_strong = True
            self._current = ""

    def handle_endtag(self, tag):
        if tag == "strong":
            self._in_strong = False
            name = self._current.strip()
            if name.lower() not in self.SKIP_NAMES and len(name) > 1:
                self.employers.append(name)

    def handle_data(self, data):
        if self._in_strong:
            self._current += data


def fetch_atr_employers():
    req = urllib.request.Request(ATR_URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        if resp.info().get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        html = data.decode("utf-8", errors="replace")
    parser = ATRParser()
    parser.feed(html)
    return parser.employers


def fetch_db_employers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name FROM employers").fetchall()
    conn.close()
    return [r[0] for r in rows]


def main():
    atr_employers = fetch_atr_employers()
    db_employers = fetch_db_employers()

    atr_norm = {normalize(e): e for e in atr_employers}
    db_norm = {normalize(e) for e in db_employers}

    new_employers = {orig for norm, orig in atr_norm.items() if norm not in db_norm}
    matched = len(atr_norm) - len(new_employers)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"=== {timestamp} ===",
        f"ATR page: {len(atr_norm)} employers found",
        f"DB: {len(db_employers)} employers",
        "",
    ]

    if new_employers:
        lines.append("NEW on ATR (not in DB):")
        for name in sorted(new_employers):
            lines.append(f"  - {name}")
    else:
        lines.append("NEW on ATR (not in DB): none")

    lines += [f"", f"NO CHANGE: {matched} matched", "===", ""]

    report = "\n".join(lines)
    print(report)

    with open(LOG_PATH, "a") as f:
        f.write(report + "\n")

    sys.exit(1 if new_employers else 0)


if __name__ == "__main__":
    main()
