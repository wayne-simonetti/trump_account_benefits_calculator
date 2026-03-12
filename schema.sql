CREATE TABLE IF NOT EXISTS zip_income (
    zip           TEXT    PRIMARY KEY,  -- 5-digit ZCTA
    median_income INTEGER,              -- NULL if Census did not report a value
    year          INTEGER               -- ACS vintage year
);

CREATE TABLE IF NOT EXISTS state_grants (
    id                    TEXT    PRIMARY KEY,
    state_code            TEXT,              -- 2-letter state; NULL = nationwide
    grantor_name          TEXT    NOT NULL,
    donor_line            TEXT,              -- subtitle line, e.g. "Ray & Barbara Dalio — $75M..."
    grant_amount          INTEGER,           -- NULL = variable/TBD
    amount_display        TEXT,              -- display override, e.g. "~$500" or "TBD"
    req_no_seed           INTEGER NOT NULL DEFAULT 0,  -- child must NOT have federal seed
    req_has_seed          INTEGER NOT NULL DEFAULT 0,  -- child must have federal seed
    req_age_max           INTEGER,           -- NULL = no age cap; else max age inclusive
    req_born_year         INTEGER,           -- NULL = any year; else exact birth year required
    req_zip_income        INTEGER NOT NULL DEFAULT 0,  -- ZIP median income must be below income_cap
    income_cap            INTEGER,           -- threshold when req_zip_income=1
    req_zip_set           TEXT,              -- JSON array of qualifying ZIPs; NULL = no ZIP restriction
    req_county_checkbox   INTEGER NOT NULL DEFAULT 0,  -- 1 = show manual checkbox(es)
    county_checkbox_label TEXT,              -- label for checkbox 1
    county_checkbox_label2 TEXT,             -- label for checkbox 2 (optional)
    note                  TEXT,
    source_url            TEXT,
    sort_order            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employers (
    id             TEXT    PRIMARY KEY,
    name           TEXT    NOT NULL,
    grant_amount   INTEGER,                         -- NULL means variable / contact HR
    condition_type TEXT    NOT NULL DEFAULT 'all'
                   CHECK(condition_type IN ('all', 'seed', 'newborn', 'conditional', 'variable')),
    group_label    TEXT    NOT NULL,
    note           TEXT,                            -- optional detail shown in grant card
    sort_order        INTEGER NOT NULL DEFAULT 0,
    contribution_type TEXT    NOT NULL DEFAULT 'seed_grant'
                      CHECK(contribution_type IN ('seed_grant', 'employer_match')),
    source_url        TEXT
);
