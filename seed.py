"""
seed.py — Create employers.db and populate it with initial data.
Run once:  python3 seed.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "trump_accounts.db"
SCHEMA  = Path(__file__).parent / "schema.sql"

EMPLOYERS = [
    # (id, name, grant_amount, condition_type, group_label, note, sort_order, contribution_type)
    ("bny_mellon",   "BNY Mellon",                      2000, "newborn",     "$2,000 one-time grant",        "newborns of U.S. employees",                              10,  "seed_grant"),
    ("ibm",          "IBM",                             1000, "conditional", "$1,000 + conditional $1,000",  "+$1,000 if family contributes $4,000+ within 24 months",  20,  "seed_grant"),
    ("blackrock",    "BlackRock",                       1000, "all",         "$1,000 one-time grant",        None,                                                      30,  "seed_grant"),
    ("steak_n_shake","Steak 'n Shake",                  1000, "seed",        "$1,000 one-time grant",        "children born 2025–2028",                                 40,  "seed_grant"),
    ("nvidia",       "Nvidia",                          1000, "all",         "$1,000 one-time grant",        None,                                                      50,  "seed_grant"),
    ("chipotle",     "Chipotle",                        1000, "all",         "$1,000 one-time grant",        None,                                                      60,  "seed_grant"),
    ("uber",         "Uber",                            1000, "all",         "$1,000 one-time grant",        None,                                                      70,  "seed_grant"),
    ("visa",         "Visa",                            1000, "all",         "$1,000 one-time grant",        None,                                                      80,  "seed_grant"),
    ("citi",         "Citi",                            1000, "seed",        "$1,000 one-time grant",        "children born 2025–2028",                                 90,  "seed_grant"),
    ("fox",          "Fox Corporation",                 1000, "seed",        "$1,000 one-time grant",        "children born 2025–2028",                                100,  "seed_grant"),
    ("newscorp",     "News Corporation",                1000, "seed",        "$1,000 one-time grant",        "children born 2025–2028",                                110,  "seed_grant"),
    ("acorns",       "Acorns",                          1000, "all",         "$1,000 one-time grant",        None,                                                     120,  "seed_grant"),
    ("statestreet",  "State Street",                    1000, "all",         "$1,000 one-time grant",        None,                                                     130,  "seed_grant"),
    ("jpmorgan",     "JPMorgan Chase",                  1000, "all",         "$1,000 one-time grant",        None,                                                     140,  "seed_grant"),
    ("robinhood",    "Robinhood",                       1000, "all",         "$1,000 one-time grant",        None,                                                     150,  "seed_grant"),
    ("chime",        "Chime",                           1000, "all",         "$1,000 one-time grant",        None,                                                     160,  "seed_grant"),
    ("sofi",         "SoFi",                            1000, "all",         "$1,000 one-time grant",        None,                                                     170,  "seed_grant"),
    ("schwab",       "Charles Schwab",                  1000, "all",         "$1,000 one-time grant",        None,                                                     180,  "seed_grant"),
    ("russell",      "Russell Investments",             1000, "all",         "$1,000 one-time grant",        None,                                                     190,  "seed_grant"),
    ("bofa",         "Bank of America",                 1000, "all",         "$1,000 one-time grant",        None,                                                     200,  "seed_grant"),
    ("coinbase",     "Coinbase",                        1000, "all",         "$1,000 one-time grant",        None,                                                     210,  "seed_grant"),
    ("empower",      "Empower",                         1000, "all",         "$1,000 one-time grant",        None,                                                     220,  "seed_grant"),
    ("intel",        "Intel",                           1000, "all",         "$1,000 one-time grant",        None,                                                     230,  "seed_grant"),
    ("ici",          "Investment Company Institute",    1000, "all",         "$1,000 one-time grant",        None,                                                     240,  "seed_grant"),
    ("tpusa",        "Turning Point USA",               1000, "all",         "$1,000 one-time grant",        None,                                                     250,  "seed_grant"),
    ("wellsfargo",   "Wells Fargo",                     None, "variable",    "Variable — contact HR",        None,                                                     260,  "seed_grant"),
    ("mastercard",   "Mastercard",                      None, "variable",    "Variable — contact HR",        None,                                                     270,  "seed_grant"),
    ("comcast",      "Comcast",                         None, "variable",    "Variable — contact HR",        None,                                                     280,  "seed_grant"),
    ("dell_corp",    "Dell Technologies",               None, "variable",    "Variable — contact HR",        "separate from Dell Foundation philanthropic grant",       290,  "seed_grant"),
    ("broadcom",     "Broadcom",                        None, "variable",    "Variable — contact HR",        None,                                                     300,  "seed_grant"),
    ("continental",  "Continental Resources",           None, "variable",    "Variable — contact HR",        None,                                                     310,  "seed_grant"),
    ("charter",      "Charter Communications",          None, "variable",    "Variable — contact HR",        None,                                                     320,  "seed_grant"),
    ("ctia",         "CTIA",                            None, "variable",    "Variable — contact HR",        None,                                                     330,  "seed_grant"),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript(SCHEMA.read_text())

    conn.executemany(
        """
        INSERT OR REPLACE INTO employers
            (id, name, grant_amount, condition_type, group_label, note, sort_order, contribution_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        EMPLOYERS,
    )

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM employers").fetchone()[0]
    conn.close()

    print(f"✓ employers.db created at {DB_PATH}")
    print(f"  {count} employer records inserted")

if __name__ == "__main__":
    main()
