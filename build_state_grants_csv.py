"""Generate CSV of state grant data for Datawrapper upload.

Run: python3 build_state_grants_csv.py
Output: state_grants.csv (upload this to Datawrapper)
"""
import csv
import json
import re

STATE_NAMES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
    'CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia',
    'FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois',
    'IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana',
    'ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota',
    'MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada',
    'NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York',
    'NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
    'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina',
    'SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont',
    'VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming',
}

# Read state_grants.js — it's `const STATE_GRANTS = [ ... ];`
src = open('state_grants.js').read()
m = re.search(r'const STATE_GRANTS\s*=\s*(\[.*?\]);', src, re.DOTALL)
if not m: raise SystemExit('Could not parse state_grants.js')
grants = json.loads(m.group(1))

# Index by state code
by_state = {}
for g in grants:
    code = g.get('state_code')
    if code is None: continue
    by_state.setdefault(code, []).append(g)

def fmt_amount(g):
    if g.get('amount_display'): return g['amount_display']
    if g.get('grant_amount') is not None: return f"${g['grant_amount']:,}"
    return 'TBD'

rows = []
for code in sorted(STATE_NAMES):
    name = STATE_NAMES[code]
    gs = by_state.get(code, [])
    has = 'Yes' if gs else 'No'
    count = len(gs)
    if gs:
        top = gs[0]
        program = top['grantor_name']
        amount = fmt_amount(top)
        note = (top.get('note') or '').strip()
    else:
        program = ''
        amount = ''
        note = ''
    rows.append([code, name, has, count, program, amount, note])

with open('state_grants.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['State Code', 'State', 'Has Program', 'Program Count', 'Top Program', 'Amount', 'Eligibility'])
    w.writerows(rows)

n_has = sum(1 for r in rows if r[2] == 'Yes')
print(f'Wrote state_grants.csv: 51 rows, {n_has} with programs')
