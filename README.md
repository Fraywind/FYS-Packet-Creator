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
- **FYSP Past Year Enrollment and Q Reports.xlsx** is largely last year's Current Year Seminars
  file with the Q scores merged in.

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
A missing Q score is left blank. The tool never puts in a number that is not in the spreadsheet.

**Anything unclear is written down, not guessed at.** If the tool cannot decide something, it goes
into `output/README.txt` for a person to handle.

**Every run starts clean.** `output/` is emptied at the start of each run, so what is in there is
always from the most recent run and never a mix of two.

## What still needs a person

- Verifying joint appointments and co-teaching in FYSP Master before a packet cycle.
- Adding shortened forms for seminar titles the run flags.
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
4. Bump the hardcoded year labels listed in `output/README.txt`.
5. Run the tool, read `output/README.txt`, then send the packets out.

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
