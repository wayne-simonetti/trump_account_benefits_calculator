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
| `states.html` | Public state-grant directory page (loads `state_grants.js` + `philanthropic_gifts.js`) |
| `philanthropy.html` | Public philanthropy directory page (loads `philanthropic_gifts.js`) |
| `privacy.html` | Privacy policy |
| `employers.js` | Auto-generated employer data (do not edit directly) |
| `state_grants.js` | Auto-generated **government** state-program data — OK/WI/TX (do not edit directly) |
| `philanthropic_gifts.js` | Auto-generated philanthropic/donor gift data (do not edit directly) |
| `zip_income.js` | Auto-generated ZIP median-income lookup (~424KB; lazy-loaded, not preloaded) |
| `trump_accounts.db` | SQLite (employers, state_grants, philanthropic_gifts, zip_income) — gitignored; rebuild via `seed.py` |
| `employers_seed.sql` / `state_grants_seed.sql` / `philanthropic_gifts_seed.sql` | **Tracked in git** — git-side source of truth for the DB. `zip_income_seed.sql` stays gitignored (too large; regen via `census_import.py`) |
| `seed.py` | Rebuild `trump_accounts.db` from `schema.sql` + tracked `*_seed.sql` files |
| `export.py` | Exports DB → `.js` files **and** `*_seed.sql` files; **run after any DB change** |
| `census_import.py` | Downloads ACS ZIP income data into DB |
| `ingest.py` | Extracts employer + state/philanthropic grant data from text via Claude API |
| `functions/api/subscribe.js` | Signup endpoint: verifies Turnstile, writes to D1 `subscribers` table, (eventually) forwards to Kit |
| `functions/_middleware.js` | Redirects `*.pages.dev` requests to `trumpaccountbenefits.com` |
| `schema.sql` | DB schema reference |
| `wrangler.toml` | Cloudflare Pages / D1 binding config |

## Grant Data Model — which table?
- **`state_grants`** — government-funded state programs only (Oklahoma, Wisconsin, Texas). Has a `status` column (`active` | `pending`); pending = proposed/not-yet-law, shown but excluded from totals.
- **`philanthropic_gifts`** — donor/foundation/company gifts (Dell, Altimeter, Dalio, Anonymous SF, Anand, Kraken, plus informational pledges). Extra fields: `donor_type`, `total_committed`, `geo_scope` (`nationwide`|`state`|`regional`|`closed`), and `is_open_to_apply` (`1` = calculator evaluates eligibility; `0` = page-only informational, e.g. closed gifts / unstructured pledges).
- The **calculator** and **`/states`** merge both tables at load time (state programs + `is_open_to_apply=1` gifts), so eligibility and the state directory cover both. **`/philanthropy`** shows all `philanthropic_gifts` grouped by `geo_scope`.
- Both tables share the same eligibility field shape (`req_no_seed`, `req_age_max`, `req_zip_set`, etc.) so the calculator's `evaluateGrant()` works on either.

## Data Management Workflow
1. Update data in `trump_accounts.db` (via `ingest.py` or DB Browser). New donor commitments → `philanthropic_gifts`; new government programs → `state_grants`.
2. Run `python3 export.py` to regenerate the `.js` files **and** `employers_seed.sql` / `state_grants_seed.sql` / `philanthropic_gifts_seed.sql`
3. Refresh the browser
4. Commit + push **both** the regenerated `.js` files **and** the updated `*_seed.sql` files — they move together. Cloudflare Pages auto-deploys on push to `main`.

After a fresh clone, run `python3 seed.py` to rebuild `trump_accounts.db` from the tracked seed files. (If `zip_income_seed.sql` isn't present locally, run `python3 census_import.py` to repopulate ZIP income from Census.)

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

## Commit & Push Policy
**OK to commit + push without asking:**
- Data regenerations from `export.py` (`employers.js`, `state_grants.js`, `philanthropic_gifts.js`, `zip_income.js`) after a DB update
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

## Changelog
- **2026-05-28** — Added `/philanthropy` page backed by a new `philanthropic_gifts` table. Moved the 6 donor-funded programs (Dell, Altimeter, Dalio, Anonymous SF, Anand, Kraken) out of `state_grants` (now government-only: OK/WI/TX). Added 3 informational rows (Durham/Altimeter, Hamm, Minaj) with `is_open_to_apply=0`. Calculator and `/states` merge both tables (deduped by id) so eligibility and the state directory are unchanged.
