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
    req_born_year_min     INTEGER,           -- NULL = no min; else earliest eligible birth year (inclusive)
    req_born_year_max     INTEGER,           -- NULL = no max; else latest eligible birth year (inclusive)
    req_zip_income        INTEGER NOT NULL DEFAULT 0,  -- ZIP median income must be below income_cap
    income_cap            INTEGER,           -- threshold when req_zip_income=1
    req_zip_set           TEXT,              -- JSON array of qualifying ZIPs; NULL = no ZIP restriction
    req_checkbox_labels   TEXT,              -- JSON array of checkbox labels for manual eligibility; NULL = automatic
    note                  TEXT,
    source_url            TEXT,
    sort_order            INTEGER NOT NULL DEFAULT 0,
    status                TEXT    NOT NULL DEFAULT 'active'
                          CHECK(status IN ('active', 'pending'))
);

CREATE TABLE IF NOT EXISTS philanthropic_gifts (
    id                    TEXT    PRIMARY KEY,
    grantor_name          TEXT    NOT NULL,
    donor_line            TEXT,              -- subtitle line
    donor_type            TEXT,              -- 'foundation' | 'individual' | 'anonymous' | 'corporate_pledge'
    total_committed       INTEGER,           -- total $ pledged across program; NULL if unknown
    state_code            TEXT,              -- 2-letter geo restriction; NULL = nationwide
    geo_scope             TEXT    NOT NULL DEFAULT 'nationwide'
                          CHECK(geo_scope IN ('nationwide', 'state', 'regional', 'closed')),
    grant_amount          INTEGER,           -- per-child amount; NULL = variable/TBD
    amount_display        TEXT,              -- display override, e.g. "~$500" or "TBD"
    -- Eligibility (same shape as state_grants so evaluateGrant works on both):
    req_no_seed           INTEGER NOT NULL DEFAULT 0,
    req_has_seed          INTEGER NOT NULL DEFAULT 0,
    req_age_max           INTEGER,
    req_born_year_min     INTEGER,
    req_born_year_max     INTEGER,
    req_zip_income        INTEGER NOT NULL DEFAULT 0,
    income_cap            INTEGER,
    req_zip_set           TEXT,
    req_checkbox_labels   TEXT,
    -- Display + source:
    note                  TEXT,
    source_url            TEXT,
    sort_order            INTEGER NOT NULL DEFAULT 0,
    -- 1 = a child can actually apply/qualify (calculator evaluates it);
    -- 0 = informational only (closed gift, unstructured pledge) — page-only.
    is_open_to_apply      INTEGER NOT NULL DEFAULT 1
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
                      CHECK(contribution_type IN ('seed_grant', 'employer_match', 'employer_stipend')),
    source_url        TEXT,
    verified          INTEGER NOT NULL DEFAULT 0,   -- 1 = announcement confirmed by primary source
    announcement_date TEXT                          -- ISO date of original announcement
);

-- Email launch-notification signups. Lives in REMOTE D1 only (never exported
-- to a tracked seed file; never in git). Written by functions/api/subscribe.js.
CREATE TABLE IF NOT EXISTS subscribers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL UNIQUE,         -- dedup on email
    created_at  TEXT    NOT NULL,                -- ISO8601 UTC
    source      TEXT,                            -- e.g. 'calculator'
    ip_hash     TEXT,                            -- salted SHA-256 of IP; never raw IP
    kit_synced  INTEGER NOT NULL DEFAULT 0       -- 1 once forwarded to Kit
);
