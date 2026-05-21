# Trump Account Tool — Claude Instructions

## Project Overview
Single-page web calculator for Trump Account (One Big Beautiful Bill Act) child savings accounts.
Helps users determine grant eligibility and project account growth. Deployed to Cloudflare Pages at https://trumpaccountbenefits.com.

## Technical Constraints
- **Pure HTML/CSS/JS only** — no frameworks (no React, Vue, etc.), no external CDN dependencies except deliberate exceptions (Cloudflare Web Analytics auto-injected at edge; Cloudflare Turnstile lazy-loaded on signup focus)
- **No new files unless necessary** — prefer editing existing files
- **Static-first data pattern** — DB → `export.py` → `.js` files → frontend loads via `<script src="...">`
- **Local dev** — serve with `python3 -m http.server 8000`; `file://` blocks script loading
- **Python scripts** — always use `python3`, never `python`
- **Cloudflare Pages Functions** — only used for the email signup flow (`functions/api/subscribe.js` + D1) and the `.pages.dev` → `.com` redirect (`functions/_middleware.js`); data lookups stay static

## Key Files
| File | Purpose |
|------|---------|
| `index.html` | Calculator page — all HTML, CSS, JS inline |
| `employers.html` | Public employer directory page (loads `employers.js`) |
| `states.html` | Public state-grant directory page (loads `state_grants.js`) |
| `privacy.html` | Privacy policy |
| `employers.js` | Auto-generated employer data (do not edit directly) |
| `state_grants.js` | Auto-generated state/regional grant data (do not edit directly) |
| `zip_income.js` | Auto-generated ZIP median-income lookup (~424KB; lazy-loaded, not preloaded) |
| `trump_accounts.db` | SQLite (employers, state_grants, zip_income) — gitignored |
| `seed.py` | One-time DB population from `*_seed.sql` files (also gitignored) |
| `export.py` | Exports DB → JS files; **run after any DB change** |
| `census_import.py` | Downloads ACS ZIP income data into DB |
| `ingest.py` | Extracts employer + state/philanthropic grant data from text via Claude API |
| `functions/api/subscribe.js` | Signup endpoint: verifies Turnstile, writes to D1 `subscribers` table, (eventually) forwards to Kit |
| `functions/_middleware.js` | Redirects `*.pages.dev` requests to `trumpaccountbenefits.com` |
| `schema.sql` | DB schema reference |
| `wrangler.toml` | Cloudflare Pages / D1 binding config |

## Data Management Workflow
1. Update data in `trump_accounts.db` (via `seed.py`, `ingest.py`, or DB Browser)
2. Run `python3 export.py` to regenerate `employers.js`, `state_grants.js`, `zip_income.js`
3. Refresh the browser
4. Commit + push the regenerated `.js` files — Cloudflare Pages auto-deploys on push to `main`

## Domain Facts (OBBBA Trump Accounts)
- $1,000 federal seed deposit: children born Jan 1, 2025 – Dec 31, 2028
- Annual contribution cap: $5,000 (family + employer combined)
- Employer contribution sub-cap: $2,500/yr (within $5,000 cap)
- Family contributions: after-tax, withdrawn tax-free
- Employer/seed/earnings: taxed as ordinary income on withdrawal
- Withdrawals prohibited before age 18
- Account open date: July 5, 2026 (via Form 4547 or trumpaccounts.gov)
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

## Commit & Push Policy
**OK to commit + push without asking:**
- Data regenerations from `export.py` (`employers.js`, `state_grants.js`, `zip_income.js`) after a DB update
- Doc-only edits (`README.md`, `CLAUDE.md`, in-file copy that doesn't change behavior)
- Trivial copy/CSS tweaks (single-line text changes, color/spacing adjustments, typo fixes)
- Follow-on fix-ups within the same task once you've already said "push" / "just push" for it

**Always ask first before pushing:**
- Code changes to `index.html` JS logic, `functions/`, or anything in the request path
- Schema or DB-shape changes
- New files
- Anything touching secrets, auth, or D1 writes

When auto-pushing, still use the standard commit-message format with the Claude co-author trailer.

## User Preferences
- Concise responses — no unnecessary explanation
- Don't add comments, docstrings, or type annotations to unchanged code
- Don't over-engineer — minimum complexity for the task
- Ask before creating new files
