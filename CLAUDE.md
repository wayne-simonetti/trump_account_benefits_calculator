# Trump Account Tool — Claude Instructions

## Project Overview
Single-page web calculator for Trump Account (One Big Beautiful Bill Act) child savings accounts.
Helps users determine grant eligibility and project account growth.

## Technical Constraints
- **Pure HTML/CSS/JS only** — no frameworks (no React, Vue, etc.), no external CDN dependencies
- **No new files unless necessary** — prefer editing existing files
- **Static file pattern** — DB → `export.py` → `.js` files → frontend loads via `<script src="...">`
- **Local dev** — serve with `python3 -m http.server 8000`; `file://` protocol blocks script loading
- **Python scripts** — always use `python3`, never `python`

## Key Files
| File | Purpose |
|------|---------|
| `index.html` | Single-page app — all HTML, CSS, JS inline |
| `employers.js` | Auto-generated employer data (do not edit directly) |
| `zip_income.js` | Auto-generated ZIP income lookup (do not edit directly) |
| `trump_accounts.db` | SQLite database (employers + zip_income tables) |
| `seed.py` | One-time DB population |
| `export.py` | Exports DB → JS files; run after any DB change |
| `census_import.py` | Downloads ACS ZIP income data into DB |
| `ingest.py` | Extracts employer + state/philanthropic grant data from text via Claude API |

## Data Management Workflow
1. Update data in `trump_accounts.db` (via `seed.py`, `ingest.py`, or DB Browser)
2. Run `python3 export.py` to regenerate `employers.js` and `zip_income.js`
3. Refresh the browser

## Domain Facts (OBBBA Trump Accounts)
- $1,000 federal seed deposit: children born Jan 1, 2025 – Dec 31, 2028
- Annual contribution cap: $5,000 (family + employer combined)
- Employer contribution sub-cap: $2,500/yr (within $5,000 cap)
- Family contributions: after-tax, withdrawn tax-free
- Employer/seed/earnings: taxed as ordinary income on withdrawal
- Withdrawals prohibited before age 18
- Account open date: July 4, 2026 (via Form 4547 or trumpaccounts.gov)
- Philanthropic/employer seed grants exempt from $5,000 annual cap

## When to Use Plan Mode
**Always use plan mode before:**
- Any new feature that involves UX or layout decisions (where to show something, how it flows)
- Changes that touch more than 2–3 sections of `index.html`
- New data sources or schema changes
- New script files
- Anything where multiple valid approaches exist

**Plan mode not required for:**
- Single-element moves or text edits
- Bug fixes with a clear, obvious solution
- Adding a note/caveat to existing content

## User Preferences
- Concise responses — no unnecessary explanation
- Don't add comments, docstrings, or type annotations to unchanged code
- Don't over-engineer — minimum complexity for the task
- Ask before creating new files
- Never auto-commit
