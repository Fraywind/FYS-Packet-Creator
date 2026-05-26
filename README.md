# FYS Packet Creator

An internal Harvard First-Year Seminar Program tool that turns three office spreadsheets into a folder of polished PDF reports for every department.

This tool is meant for FYSP staff. The handbook (linked below) is written for people without a programming background.

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

You need Python 3.9 or newer installed. Then, from this folder:

```
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5050`.

## What it does

For each department (for example `[AAAS]`, `[HLS]`, `[SEAS]`) the tool generates:

| PDF | Title | Source |
|-----|-------|--------|
| 1 | Number of First-Year Seminars by Academic Year | SAVED.xlsx |
| 2 | Percentage of Seminars by Faculty Rank | SAVED.xlsx |
| 4 | Seminars Taught per Year per Rank | SAVED.xlsx |
| 5 | Faculty Teaching Seminars by Name | SAVED.xlsx |
| 6 | Current Year Enrollment Report | APPLICATION_CURRENT.xlsx |
| 7 | Prior Year Enrollment and Evaluations | HOLYGRAIL.xlsx |
| ALL | Combined packet with all of the above | All three files |

PDF 3 (3D Map) is not produced by this tool. See the handbook for the recommended approach.

## Documentation

For complete instructions, the spreadsheet formats, where the files come from, and a yearly maintenance checklist, read the handbook:

- While the app is running, click "Read the handbook" in the top right of the page.
- Or open `static/docs.html` directly in any browser (no server needed).

## Spreadsheet quick reference

For full details (notation, special cases, how to update each year), see the handbook.

**SAVED.xlsx** &middot; Columns: `Professor`, `Rank`, `Department`, then one column per academic year (for example `2014-15`, `2015-16`). Each year cell uses one of: `X`, `XX`, `X*`, `X!`, `X!!`.

**APPLICATION_CURRENT.xlsx** &middot; Columns: `Department`, `Sem#`, `Term`, `Title`, `Fname`, `LName`, `Total Appl Count`, `Placed`.

**HOLYGRAIL.xlsx** &middot; Columns: `DEPT`, `SEM#`, `TERM`, `TITLE`, `FIRST  NAME` (two spaces), `LAST NAME`, `APPL#`, `ENROLL`, `SEMQ`, `INST Q`. We recommend renaming this file in the future to something clearer such as `EVALUATIONS_PRIOR.xlsx`.

## Stopping the server

Close the terminal window that started the server, or press `Ctrl+C` in it.
