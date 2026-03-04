# Trump Account Benefits Calculator

A single-page web calculator for the **Trump Account** program established by the One Big Beautiful Bill Act (OBBBA). Helps parents determine grant eligibility and project long-term account growth for their child's tax-advantaged savings account.

🔗 **[Live Calculator](https://trump-account-benefits-calculator.pages.dev)**

---

## Features

- **Grant eligibility engine** — automatically determines eligibility for federal, philanthropic, state/regional, and employer grants based on child's birth date, ZIP code, state, and employer
- **Employer grant directory** — searchable table of 34+ employers with known Trump Account grants or matches
- **Dual-range contribution slider** — set the age window during which you plan to contribute
- **Employer annual match auto-detection** — employer match populates automatically from your employer selection
- **Account growth projection** — compound growth chart and year-by-year breakdown to ages 18, 22, or 30
- **ZIP income lookup** — 30,000+ ZIP codes from Census ACS data to auto-check income-based grant eligibility

---

## Trump Account Basics (OBBBA)

| Detail | Info |
|--------|------|
| Federal seed deposit | $1,000 for children born Jan 1, 2025 – Dec 31, 2028 |
| Annual contribution cap | $5,000 (family + employer combined) |
| Employer contribution sub-cap | $2,500/yr (within the $5,000 cap) |
| Family contributions | After-tax in, tax-free out |
| Employer/seed/earnings | Taxed as ordinary income on withdrawal |
| Withdrawals | Prohibited before age 18 |
| Account open date | July 4, 2026 (via Form 4547 or trumpaccounts.gov) |

---

## Tech Stack

- Pure HTML/CSS/JS — no frameworks, no external dependencies
- Inline canvas chart (no Chart.js)
- SQLite database (`trump_accounts.db`) for employer and ZIP income data
- Static JS exports (`employers.js`, `zip_income.js`) loaded by the frontend

---

## Local Development

```bash
# Serve locally (file:// won't work due to script loading)
python3 -m http.server 8000
# Open http://localhost:8000
```

## Data Management

```bash
# After updating trump_accounts.db, regenerate JS files:
python3 export.py

# Import Census ACS ZIP income data:
python3 census_import.py

# Ingest employer grant data from tweet text via Claude API:
export ANTHROPIC_API_KEY=your_key_here
python3 tweet_ingest.py
```

---

## Sources

- [IRS Trump Accounts](https://www.irs.gov/trumpaccounts)
- [trumpaccounts.gov](https://www.trumpaccounts.gov/)
- [Americans for Tax Reform — Contributors List](https://atr.org/trumpaccounts/)
- [SavingForCollege — 50 State Challenge](https://www.savingforcollege.com/article/trump-account-new-corporate-benefits-state-programs)

---

*For informational purposes only. Grant programs are pledges — amounts, eligibility, and distribution processes may change. Consult a qualified financial advisor before making financial decisions.*
