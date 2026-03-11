CREATE TABLE IF NOT EXISTS zip_income (
    zip           TEXT    PRIMARY KEY,  -- 5-digit ZCTA
    median_income INTEGER,              -- NULL if Census did not report a value
    year          INTEGER               -- ACS vintage year
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
