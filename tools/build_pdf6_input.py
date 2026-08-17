"""Build the PDF 6 input spreadsheet for an upcoming academic year.

The registrar's enrollment export (FYSEMR_SeminarEnrollment_Table_YYYY-YYYY.xlsx)
has the application and enrollment counts but no seminar numbers and no
departments, and it puts co-taught seminars on a single row. PDF 6 needs all
three. This script fills the gaps and writes a spreadsheet in the shape PDF 6
already reads.

Sources:
  1. The registrar's enrollment export      -> title, instructors, apps, placed
  2. The public seminar catalog page        -> seminar number (SEM#)
     https://firstyearseminarprogram.college.harvard.edu/seminars/
  3. FYSP Master Packet Data.xlsx           -> department, incl. "D1 / D2" for
                                               joint appointments

Run it once a year, when the application cycle and course registration have both
closed, then upload the result as the APPLICATION_CURRENT file.

    python3 tools/build_pdf6_input.py \
        --enrollment ~/Downloads/FYSEMR_SeminarEnrollment_Table_2026-2027.xlsx \
        --master ~/Downloads/"FYSP Master Packet Data.xlsx" \
        --year 2026-27 \
        --out ~/Downloads/"APPLICATION_CURRENT 2026-2027.xlsx"

Anything it cannot resolve is listed at the end of the run rather than guessed.
"""

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request

import pandas as pd

sys.path.insert(0, __file__.rsplit('/tools/', 1)[0])
from generators.shared import DEPARTMENT_MAPPING  # noqa: E402

CATALOG_URL = 'https://firstyearseminarprogram.college.harvard.edu/seminars/'

# Names the registrar's export writes differently from the master roster, where
# normalizing accents and punctuation is not enough to match them up. Maps
# "lastname, firstinitial" as it appears in the export -> as it appears in the
# master. Redundant surnames (Hill vs Hills, Davis, Lee) are deliberately absent:
# those are different people and must never be merged.
NAME_ALIASES = {
    'mankiw, n': 'mankiw, g',            # N. Gregory Mankiw
    'fash, b': 'fash, w',                # Bill = William Fash
    'vivo, i': 'de vivo, i',             # surname particle dropped in the export
    'lamberth, c': 'bickel lamberth, c',  # Courtney Bickel Lamberth
}


def strip_accents(text):
    text = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in text if not unicodedata.combining(c))


def person_key(last, first):
    """Roster-style 'lastname, firstinitial' key, accent- and marker-free."""
    last = strip_accents(last).strip().rstrip('*').strip().lower()
    first = strip_accents(first).strip().lstrip('.').strip()
    key = f"{last}, {first[0].lower()}" if first else last
    return NAME_ALIASES.get(key, key)


def title_key(title):
    return re.sub(r'[^a-z0-9]', '', strip_accents(title).replace('’', "'").lower())


def term_key(term):
    """Normalize '2026 Fall' and 'Fall 2026' to the same 'Fall 2026'."""
    term = str(term).strip()
    match = re.match(r'(Fall|Spring)\s+(\d{4})', term)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    match = re.match(r'(\d{4})\s+(Fall|Spring)', term)
    if match:
        return f"{match.group(2)} {match.group(1)}"
    return term


def season(term):
    return 'Spring' if 'spring' in str(term).lower() else 'Fall'


def fetch_catalog(source):
    """Parse the seminar catalog into {(title_key, term_key): {...}}."""
    if source and not source.startswith('http'):
        page = open(source, encoding='utf-8').read()
    else:
        request = urllib.request.Request(source or CATALOG_URL,
                                         headers={'User-Agent': 'Mozilla/5.0'})
        page = urllib.request.urlopen(request, timeout=60).read().decode('utf-8')

    entries = re.findall(
        r'<h3 class="h h4 h-style-disable cp-dir-field-post_title" data-value="(.*?)">'
        r'.*?<span class="cp-dir-field-post_excerpt" data-value="">(.*?)</span>',
        page, re.S)

    catalog = {}
    for raw_title, excerpt in entries:
        title = html.unescape(raw_title).strip()
        excerpt = html.unescape(excerpt.replace('&nbsp;', ' '))
        match = re.search(r'First-Year Seminar\s+([0-9]+[A-Z]?)\s*\|\s*'
                          r'(\d{4}\s+(?:Fall|Spring))', excerpt)
        if not match:
            continue
        sem, term = match.group(1), match.group(2)

        people = []
        block = re.search(r'^\s*<strong>(.*?)</strong>', excerpt, re.S)
        if block:
            for name, dept in re.findall(r'<a [^>]*>(.*?)</a>\s*\(([^)]*)\)',
                                         block.group(1), re.S):
                people.append((re.sub('<[^>]+>', '', name).strip(), dept.strip()))

        # Seminars offered in two sections appear twice with the same number;
        # the enrollment export merges them, so one entry per key is correct.
        catalog.setdefault((title_key(title), term_key(term)),
                           {'sem': sem, 'people': people})
    return catalog


def load_master_departments(path, year_column):
    """{person_key: 'DEPT'} or 'D1 / D2' for a joint appointment."""
    master = pd.read_excel(path)
    if year_column and year_column not in master.columns:
        raise SystemExit(f"--year {year_column} is not a column in the master "
                         f"(have: {[c for c in master.columns if '-' in str(c)]})")

    departments = {}
    for _, row in master.iterrows():
        professor = str(row.get('Professor', '')).strip()
        dept = str(row.get('Department', '')).strip()
        if not professor or professor == 'nan' or not dept or dept == 'nan':
            continue
        if year_column and pd.isna(row.get(year_column)):
            continue  # not teaching this cycle
        last, _, first = professor.partition(',')
        key = person_key(last, first)
        departments.setdefault(key, [])
        if dept not in departments[key]:
            departments[key].append(dept)
    return {k: ' / '.join(v) for k, v in departments.items()}


def split_instructors(fname, lname):
    """Co-taught rows carry both names comma-separated in each column."""
    firsts = [p.strip() for p in str(fname).split(',')]
    lasts = [p.strip() for p in str(lname).split(',')]
    if len(firsts) == len(lasts) and len(firsts) > 1:
        return list(zip(firsts, lasts))
    return [(str(fname).strip(), str(lname).strip())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enrollment', required=True)
    parser.add_argument('--master', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--year', default=None,
                        help="Master column for this cycle, e.g. 2026-27. Limits "
                             "the department lookup to faculty teaching that year.")
    parser.add_argument('--catalog', default=None,
                        help='Catalog URL or a saved copy of the page. Defaults to '
                             'the live site.')
    args = parser.parse_args()

    enrollment = pd.read_excel(args.enrollment)
    catalog = fetch_catalog(args.catalog)
    master_departments = load_master_departments(args.master, args.year)
    catalog_departments = {v: k for k, v in DEPARTMENT_MAPPING.items()}

    rows, no_number, no_department = [], [], []
    for _, row in enrollment.iterrows():
        title = str(row['Title']).strip()
        key = (title_key(title), term_key(row['Term']))
        entry = catalog.get(key, {})
        if not entry:
            no_number.append(f"{row['Term']} | {title}")

        # The catalog names each co-teacher's own department, which is the
        # fallback when someone is missing from the master roster.
        catalog_people = {person_key(p.split()[-1], p.split()[0]): d
                          for p, d in entry.get('people', [])}

        for first, last in split_instructors(row['Fname'], row['LName']):
            key_person = person_key(last, first)
            dept = master_departments.get(key_person)
            if not dept:
                raw = catalog_people.get(key_person, '')
                # Catalog prints full department names, sometimes several joined
                # by "and"; keep only the ones the packet knows about.
                found = [DEPARTMENT_MAPPING[name] for name in DEPARTMENT_MAPPING
                         if name.lower() in raw.lower()]
                dept = ' / '.join(sorted(set(found)))
                if dept:
                    no_department.append(
                        f"{first} {last} -> {dept} (from catalog, not in master)")
            if not dept:
                no_department.append(f"{first} {last} -> UNRESOLVED ({title})")
                continue

            rows.append({
                'Department': dept,
                'Sem#': entry.get('sem', ''),
                'Title': title,
                'Fname': first,
                'LName': last,
                'Term': season(row['Term']),
                'Total Appl Count': row.get('Total Appl Count', ''),
                'Placed': row.get('Placed', ''),
            })

    out = pd.DataFrame(rows, columns=['Department', 'Sem#', 'Title', 'Fname',
                                      'LName', 'Term', 'Total Appl Count', 'Placed'])
    out.to_excel(args.out, index=False)

    print(f"enrollment rows read : {len(enrollment)}")
    print(f"instructor rows out  : {len(out)}  "
          f"(Fall {sum(out['Term'] == 'Fall')}, Spring {sum(out['Term'] == 'Spring')})")
    print(f"departments covered  : {out['Department'].nunique()}")
    print(f"written              : {args.out}")
    for label, items in (('NO SEMINAR NUMBER', no_number),
                         ('DEPARTMENT NEEDS A LOOK', no_department)):
        if items:
            print(f"\n{label}:")
            for item in items:
                print(f"  - {item}")


if __name__ == '__main__':
    main()
