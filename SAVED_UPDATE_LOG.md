# SAVED.xlsx Update Log

## 2026-27 Column Addition (June 2026)

This log documents the process, rules, and edge cases encountered when adding
the `2026-27` column to `SAVED.xlsx` using the `teaching26-27.xlsx` roster.

---

### Source Files

- **SAVED.xlsx** — Master faculty spreadsheet. Professors listed as `LastName, FirstInitial`
  (e.g., `Agbiboa, D`). Columns are: Department, Professor, Rank, then one column per
  academic year (2013-14 through 2025-26, now 2026-27).
- **teaching26-27.xlsx** — Teaching roster for 2026-27. The authoritative sheet is `MASTER`,
  with columns: classCatalogNumber, courseTitle, instructorName. Instructor names are full
  names (e.g., `Daniel Agbiboa`). Co-taught seminars appear as semicolon-separated names
  in one instructorName cell (e.g., `Sien Verschave; Daniel Kahne`).

---

### Marker Rules for Each Cell

| Marker | Meaning |
|--------|---------|
| `X`    | Taught one seminar, listed in one department in SAVED |
| `XX`   | Taught two or more distinct seminars this year |
| `X*`   | Joint appointment (appears in 2+ departments in SAVED) OR co-taught a seminar with another instructor |

The `X*` rule covers both cases because the PDF5 legend treats joint appointments
and co-teaching identically (0.5 score, half-circle symbol).

---

### Name Format Matching

Teaching rosters use full names; SAVED uses `LastName, FirstInitial`. Conversion:

1. Split full name on spaces, take last word as last name, first letter of first word as initial.
2. Look up `LastName, F` in SAVED (case-insensitive, Unicode-normalized).
3. Handle special cases via an alias table (see below).

**Aliases and known discrepancies resolved:**

| Full name in roster | Saved as in SAVED | Note |
|---------------------|-------------------|------|
| Bill Fash | Fash, W | "Bill" is a nickname for William |
| N. Mankiw | Mankiw, G | Goes by Gregory (G) in SAVED, not N |
| C. Vafa | Vafa, C | Cumrun Vafa, first letter only in roster |
| Jeff W. Lichtman | Lichtman, J | Middle initial in roster |
| James H. Stock | Stock, J | Middle initial in roster |
| Aravinthan Samuel | Samuel, A | Roster spells Aravinthan; SAVED has Aravintham |
| Evridiki Georganteli | Georganteli, E | Roster: Evridiki; elsewhere: Eurydice |
| Ashley Villar | Villar, A | Roster: Ashley; some sheets say Victoria — use Ashley (ASTRO confirmed) |
| Josh Bell | Bell, J | No match in SAVED — see flagged entries |
| Javier Ortega-Hernandez | Ortega-Hernández, J | Accent normalized for lookup |
| Joanna Aizenberg | Aizenberg, J* | SAVED stores name with trailing asterisk |
| Nancy Hill | Hill, N. | SAVED stores name with trailing period |
| Immaculata De Vivo | De Vivo, I | Space in last name; HSPH row |
| Jan Ziolkowski | Ziolkowsky, J | Typo in SAVED (extra y); CLASS row |

---

### Co-Taught Seminars (2026-27)

These seminars have two instructors. Both instructors get `X*` in their respective
department rows (even if they are in different departments).

| Seminar | Instructors |
|---------|-------------|
| 52T | Sien Verschave (MCB) + Daniel Kahne (CHEM) |
| 54F | Venkatesh Murthy (MCB) + Katie Quast (not in SAVED — flagged) |
| 58C | Jeff W. Lichtman (MCB) + Logan McCarty (PHYS) |

---

### Duplicate Seminar Entries in Roster (not co-teaching)

Some seminars appear twice in the MASTER sheet with the same instructor. These are
data artifacts (two sections or a duplicate row), not actual two-instructor courses.
Treat as a single seminar (marker = `X`, not `XX`).

| Seminar | Instructor |
|---------|-----------|
| 23R | Charles Alcock |
| 54I | Douglas Finkbeiner |
| 54J | Alyssa Goodman |
| 71Y | Michael Norton |

---

### Two-Seminar Instructors (XX)

| Instructor | Seminars |
|-----------|---------|
| Nathan Melenbrink (PHYS) | 53J + 58E |

---

### Flagged Entries — Needs Manual Entry in SAVED

These instructors appear in the 2026-27 teaching roster but could not be
confidently matched to a row in SAVED.xlsx. Enter them manually.

| Instructor | Seminar | Reason |
|-----------|---------|--------|
| Courtney Lamberth | 68N | SAVED has `Bickel Lamberth, C` [STUOFREL] — may be the same person (Courtney Bickel Lamberth). Confirm before writing. |
| David Hempton | 68F | Not in SAVED. New instructor? Department unknown — likely HDS or STUOFREL (Divinity). |
| Josh Bell | 68J | Not in SAVED. New instructor. |
| Katie Quast | 54F (co-teaches with Murthy) | Not in SAVED. New instructor. |
| Kevin Croke | 75D | Not in SAVED. New instructor. |
| Simone Stirner | 68D | Not in SAVED. New instructor. |
| Stephen Sachs | 73Y | SAVED has `Sachs, B` [HLS] — different person (different initial). Sachs, S needs to be added if he is new. |

---

### Note for Sabrina (June 2026)

Non-FAS packets are shaky -- they were a lower priority when this was built. It is good to double
check with Ofrit and flesh those out before relying on them.

---

### Joint Appointment Verification (26-27 Column)

When the 2026-27 column was initially written, some professors were marked X* based on how they
appear in SAVED (i.e., listed in 2+ departments). However, some of those multi-department listings
in SAVED are themselves errors or outdated. Two confirmed incorrect joint labels found in June 2026:

- **Becker, A** -- listed in both ANTH and HMS in SAVED, but she is HMS only. Not joint.
- **Farrell, B** -- listed in both EPS and OEB in SAVED, but he is OEB only. Not joint.

As a result, ALL X* markers in the 2026-27 column were reset to X (June 2026) so that joint
status can be re-verified by hand before publishing. Below is the full list of everyone who had
been marked X*, grouped by appointment type:

**Joint appointment (appeared in 2+ dept rows in SAVED):**

| Professor | Departments labeled in SAVED |
|-----------|------------------------------|
| Abe, R | EASIAN + STUOFREL |
| Becker, A | ANTH + HMS (confirmed NOT joint -- HMS only) |
| Brown-Nagin, T | HIST + HLS |
| Davis, C | Gov + OEB |
| Deming, D | HKS + HGSE |
| Farrell, B | EPS + OEB (confirmed NOT joint -- OEB only) |
| Finkbeiner, D | ASTRO + PHYS |
| Kelsey, R | HAA + TDM |
| Lamberth, D | HDS + STUOFREL |
| Lewis, S | AAAS + HAA |
| Manuelian, P | ANTH + NELC |
| Patton, K | HDS + STUOFREL |
| Reinert, S | HBS + HIST |
| Shelby, T | AAAS + PHIL |
| Straneo, F | EPS + SEAS |
| Wang, E | HAA + STUOFREL + TDM |
| Zeghal, M | NELC + STUOFREL |

**Co-teaching only (appeared in 1 dept row in SAVED -- X* is for co-teaching, not joint appt):**

| Professor | Dept | Co-teaches with |
|-----------|------|-----------------|
| Kahne, D | CHEM | Verschave, S (seminar 52T) |
| Lichtman, J | MCB | McCarty, L (seminar 58C) |
| Murthy, V | MCB | Katie Quast (seminar 54F -- Quast not yet in SAVED) |
| Verschave, S | MCB | Kahne, D (seminar 52T) |
| McCarty, L | PHYS | Lichtman, J (seminar 58C) |

The co-teaching X* entries are straightforward. The joint appointment entries above need human
verification against the current faculty directory before being restored to X*.

---

### Edge Case Notes

- **Short or common names (e.g., Lee, J):** Multiple people with the same last name and
  first initial exist across departments. Do NOT auto-match for these. Always surface to
  the human for manual review. This applies to any name where the `LastName, Initial`
  combination appears in more than one department with genuinely different people.

- **Joint appointments:** A professor listed in 2 or more departments in SAVED gets `X*`
  in ALL their department rows for the year they teach, even if they only teach one seminar.
  This is consistent with how prior years are coded (the PDF5 half-circle symbol).

- **New instructors not in SAVED:** When an instructor appears in the teaching roster but
  has no matching row in SAVED, do not auto-add them. Flag for human review to determine
  the correct department, rank, and whether they are genuinely new or just named differently.

- **Accented/Unicode names:** Normalize to ASCII for matching (e.g., Hernández → Hernandez),
  but preserve the original spelling in SAVED when writing.

- **Nickname vs. official name:** Some instructors go by shortened names (Bill for William,
  etc.). Maintain an alias table and update it each year as new cases arise.
