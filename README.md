# FYS Packet Creator

An internal Harvard First-Year Seminar Program tool. It turns three office spreadsheets into a
folder of finished PDF reports for every department, one packet per department.

Built for FYSP staff. The handbook (linked below) assumes no programming background.

## Quick start

### Windows

1. Double-click **`start.bat`** in this folder.
2. Wait for it to install dependencies (first run only) and start the server.
3. A browser tab opens at `http://localhost:5050`.

### macOS or Linux

1. Open a Terminal in this folder.
2. Run **`./start.sh`** (you may need to `chmod +x start.sh` once).
3. Open `http://localhost:5050` in your browser.

### If the start scripts do not work

You need Python 3.9 or newer. Then, from this folder:

```
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5050`.

## What you need before you start

Three spreadsheets. Upload all three for a complete packet. Any file you leave out simply skips
its own pages, and the rest of the packet is still produced.

| File | Feeds | What it is | When it is ready |
|------|-------|-----------|------------------|
| **FYSP Master.xlsx** | Pages 1, 2, 3, 4, 5 | Faculty teaching history, one column per academic year | Maintained year-round, updated once the new teaching roster is out |
| **FYSP Current Year Seminars.xlsx** | Page 6 | The seminars running this year, with applications and placements | Usually once the course registration deadline has passed |
| **FYSP Past Year Enrollment and Q Reports.xlsx** | Page 7 | Last year's enrollment with Q report scores merged in | After HCIR releases the Q reports |

Notes on each:

- **FYSP Master.xlsx** has its new academic-year column written by a separate project,
  [FYS-New-Year-Matching](#related-projects). This tool only reads the file.
- **FYSP Current Year Seminars.xlsx** is built with `tools/build_pdf6_input.py` from the registrar
  enrollment export.
- **FYSP Past Year Enrollment and Q Reports.xlsx** starts as last year's Current Year Seminars
  file with the Q scores merged in, and then has its enrollment column replaced with the
  registrar's real end-of-term counts by `tools/build_pdf7_input.py`. That second step is not
  optional: see [What "Enrolled" means on each page](#what-enrolled-means-on-each-page).

The upload slots go by position on the page, not by file name, so a file that is still named
something else on disk uploads into the right slot.

## What you get

For each department (for example `[AAAS]`, `[HLS]`, `[SEAS]`):

| PDF | Title | Source |
|-----|-------|--------|
| 1 | Number of First-Year Seminars by Academic Year | FYSP Master.xlsx |
| 2 | Percentage of Seminars by Faculty Rank | FYSP Master.xlsx |
| 3 | Seminars Taught per Year (3D graph) | FYSP Master.xlsx |
| 4 | Seminars Taught per Year per Rank | FYSP Master.xlsx |
| 5 | Faculty Teaching Seminars by Name | FYSP Master.xlsx |
| 6 | Current Year Enrollment Report | FYSP Current Year Seminars.xlsx |
| 7 | Prior Year Enrollment and Evaluations | FYSP Past Year Enrollment and Q Reports.xlsx |
| ALL | Combined packet with all of the above | All three files |

Everything lands in `output/`, one folder per department, plus a notes file.

## Read the notes before you send anything out

Every run writes **`output/README.txt`**. The page shows it when the run finishes, and it travels
inside the "Download all" ZIP. Read it. It records:

- Which of the three source files were used, and which pages are missing because a file was not
  uploaded.
- Departments present in the data but intentionally left out of the packets.
- Seminar titles too long to print on one line, and what to do about them.
- Tables that had to start a year later to fit on the page (see the rule below).
- Any errors during generation.
- The year labels that are hardcoded and must be bumped by one next cycle.

If nothing needs a second look, the page says so and the notes are still one click away.

## Rules the tool follows

These are the decisions the tool makes on its own, so you know what to expect.

**Every page fits on its paper.** Nothing is ever printed past the edge and nothing overlaps.

- *Long seminar titles* (pages 6 and 7) shrink slightly to stay on one line. If a title would have
  to shrink past the smallest readable size, a shortened form from `TITLE_OVERRIDES` in
  `generators/shared.py` is used instead, cut at the title's own colon or dash. A title long enough
  to need shortening but not listed there wraps onto a second line, and the run reports it so a
  person can add a shortened form.
- *Wide tables* (pages 4 and 5) drop their oldest year columns, one at a time, until the table fits
  across the page. This only happens to the departments that would otherwise be cut, and only for
  left and right overflow. A department with long faculty names pushes the table wider than the
  paper, and an over-wide table is centered, so it is cut at both edges at once: the first letter of
  every name and the newest year column. Starting a year later (2014-15 rather than 2013-14) keeps
  the year headings spelled out the same as every other department. The run reports exactly which
  departments and which years.

**Nothing is filled in for you.** A department with no rows in a file gets no page from that file.
A seminar that ran without a Q score reads "N/A", written that way in the source spreadsheet
rather than invented by the tool, and page 7 prints it as it stands. Where one of the two scores
exists and the other does not, only the missing one reads "N/A" (2025-26: Anne Becker's 71X has a
seminar score but no instructor score). The tool never puts in a number that is not in the
spreadsheet.

**Anything unclear is written down, not guessed at.** If the tool cannot decide something, it goes
into `output/README.txt` for a person to handle.

**Every run starts clean.** `output/` is emptied at the start of each run, so what is in there is
always from the most recent run and never a mix of two.

## Departments, and the one that is not a department

Department cells hold either one department or a joint pair ("COMPLIT / ENGL"), and a department
matches when it equals one of the parts. It is not a substring test. That distinction is the whole
point: **"Committee on Degrees in Social Studies" is not Sociology.** A substring test put its two
seminars (Winston Berg's 74D and Bréond Durr's 74E) onto the SOC packet, because "SOC" sits inside
"Social". Sociology's page 7 is Robert Sampson and Shai Dromi and no one else.

**No packet is produced for the Committee.** It is in the source data for documentation and
accounting only, it is listed in `EXCLUDED_DEPTS` in `app.py`, and every run names it in
`output/README.txt` so the omission reads as a decision rather than a failure. In the master
spreadsheet those rows carry their department **struck through**, which is the office's own marker
for the same thing; the tool keys off the name, not the formatting.

A consequence worth knowing: the Committee's seminars count toward the program totals on page 1 but
reach no department packet.

## One instructor, two spellings

Pages 6 and 7 read different spreadsheets, so the same person can arrive written two ways and read
as two people. 2025-26 had four: Sun Kim against Sun Joo Kim, N. Mankiw against N. Gregory Mankiw,
Katie Quast against Kathleen Quast, and C. Vafa against Cumrun Vafa. The fuller form wins, and the
decision is recorded in `PERSON_NAME_OVERRIDES` in `generators/shared.py`.

Names are keyed by **surname plus first initial, never surname alone**. David and Philip Fisher are
different people, and so are Jessica and Stephen Marglin, Courtney and David Lamberth, and Anna and
Benjamin Wilson. Keying on surname would have merged four pairs of real people.

Every run compares the two pages and lists anything still disagreeing in `output/README.txt` for a
person to settle. Nothing is renamed automatically: a name the tool has not been told about prints
on each page exactly as its own spreadsheet writes it.

## Counting seminars for page 1

Page 1 counts **offerings, not seminar numbers**, excluding anything the registrar marks CANCELLED.
A professor who teaches two full classes in one year counts twice, whether that is the same seminar
in both terms or two sections of it in one term. In the master that is the `XX` marker, which
scores 2 on pages 3 and 4 through the shared rank aggregation, in that professor's own department
and in that year's column only.

A `B` on a marker (`XB`, `X*B`, `XB*`) says the professor has since retired, left Harvard, or died
while teaching. It says something about the person today, not about whether the seminar ran, so it
never changes a score: `XB` counts as `X`, `X*B` and `XB*` as `X*`. Page 5 prints those markers in
black, which is where a reader learns it.

2025-26 is 122: Fall 78 and Spring 44. Two of those are second sections that are easy to miss,
because the application and Q files each show one row where two classes ran:

- **Mankiw 43J**, two Fall sections. The application file gives it away with `Capacity` 24 where
  the normal seminar is 12 or 15.
- **52T**, two Spring sections with different co-teaching pairs, settled by the registrar's class
  numbers 13241 and 17682.

A hidden second section shows up as a doubled `Capacity`, and only a class-number export proves it.
Trust the master's `XX` over the application and Q files here: the master is built from the
class-row-level my.harvard roster and is the only source that can see sections at all.

## What "Enrolled" means on each page

Pages 6 and 7 both print a column headed **Enrolled**, and the two years mean different things by
it. Getting these confused is the one mistake in this pipeline that produces a page which looks
completely normal and is wrong on every row, so it is worth being deliberate about.

| | Page 6 | Page 7 |
|---|---|---|
| Year | The upcoming one | The one that just finished |
| Has the seminar run? | No | Yes |
| Number that exists | Lottery placement only | The registrar's actual enrollment |
| Column read | `Placed` | `ENROLL ` |
| Built by | `tools/build_pdf6_input.py` | `tools/build_pdf7_input.py` |

Page 6 uses placement **on purpose**, and says so on the page: "Enrolled - As of the Fall Course
Registration Deadline". For a year that has not started, placement is the only number there is.

Page 7 must not. That year is over, the registrar has real counts, and the page sets those numbers
beside Q scores earned by the students who actually finished the course. A placement number there
is not a rounding error, it is a different quantity.

The two get confused because page 7's input begins life as last year's page 6 file, which carries
`Placed`. If the Q files that get merged in happen to carry real enrollment, the mistake is
covered up; if they do not, the placements survive into the packet.

**2025-2026 is the worked example.** `FALL 2025 Q SCORES.xlsx` has a `Students_Enrolled` column, so
all 79 fall rows came out right. The spring Q file has only Q averages, so all 46 spring rows kept
their August placements. Homi Bhabha's 63N printed 15, which was its capacity and its placement,
next to a Q score earned by the 4 students who finished it. Running `tools/build_pdf7_input.py`
against the registrar's spring export corrected 40 rows and left fall untouched.

**Which registrar column counts as enrolled** is a genuine choice, so it is a flag on the script
rather than a constant. The default is the add/drop column (`Enrollment as of Feb. 3rd` in the
spring export), because that is the roster that sat the course and produced the Q scores printed
beside it. The registration-day column counts students who registered and then dropped, and runs
several students higher per seminar.

## What still needs a person

- Verifying joint appointments and co-teaching in FYSP Master before a packet cycle.
- Adding shortened forms for seminar titles the run flags.
- Deciding who taught a seminar when the registrar export and the application system disagree.
  `tools/build_pdf7_input.py` reports these rather than picking one.
- Settling an instructor written two ways across pages 6 and 7. Each run lists them in
  `output/README.txt`; the decision goes in `PERSON_NAME_OVERRIDES` in `generators/shared.py`.
- Bumping the hardcoded year labels each cycle. `output/README.txt` lists them with the exact file
  and the value they need.
- Non-FAS packets (HBS, HDS, HGSE, HKS, HLS, HMS, HSPH) were a lower priority when this was built.
  Check them with the office before relying on them.

## Yearly cycle

1. Add the new academic-year column to FYSP Master (see
   [FYS-New-Year-Matching](#related-projects)).
2. Once course registration closes, build FYSP Current Year Seminars with
   `tools/build_pdf6_input.py`.
3. Merge last year's Q report scores into last year's Current Year Seminars file to produce the
   new FYSP Past Year Enrollment and Q Reports.
4. Replace that file's enrollment column with the registrar's real end-of-term counts using
   `tools/build_pdf7_input.py`, once the term enrollment exports are out. Skipping this leaves
   August placements on page 7. See
   [What "Enrolled" means on each page](#what-enrolled-means-on-each-page).
5. Bump the hardcoded year labels listed in `output/README.txt`.
6. Run the tool, read `output/README.txt`, then send the packets out.

## Documentation

For the full instructions, spreadsheet formats, where each file comes from, and the maintenance
checklist, read the staff guide:

- While the app is running, click "Read the guide" in the top right of the page.
- Or open `static/instructions.html` directly in any browser (no server needed).

## Spreadsheet quick reference

Full details, notation, and special cases are in the handbook.

**FYSP Master.xlsx**. Columns: `Professor`, `Rank`, `Department`, then one column per academic year
(for example `2014-15`, `2015-16`). Each year cell uses one of `X`, `XX`, `X*`, `X!`, `X!!`,
`XXSTAR`.

**FYSP Current Year Seminars.xlsx**. Columns: `Department`, `Sem#`, `Term`, `Title`, `Fname`,
`LName`, `Total Appl Count`, `Placed`.

**FYSP Past Year Enrollment and Q Reports.xlsx**. Columns: `DEPT`, `SEM#`, `TERM`, `TITLE`,
`FIRST  NAME` (two spaces), `LAST NAME`, `APPL#`, `ENROLL`, `SEMQ`, `INST Q`.

## Related projects

**FYS-New-Year-Matching** is a separate, standalone project that writes the new academic-year
column into FYSP Master from the my.harvard teaching roster. It has its own rules for markers,
aliases, and names that must never be auto-matched. This repo only consumes the result.

## Stopping the server

Close the terminal window that started the server, or press `Ctrl+C` in it.
