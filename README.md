# FYS Packet Creator

Web application for generating First-Year Seminar Program (FYSP) department packets. Upload spreadsheets, generate PDFs for all departments, preview results in-browser, and download organized output.

## What It Generates

For each department (e.g., [AAAS], [HLS], [SEAS], etc.), the tool creates:

| PDF | Title | Data Source |
|-----|-------|-------------|
| 1 | # of First-Year Seminars by Academic Year | SAVED.xlsx |
| 2 | % of Seminars According to Faculty Rank | SAVED.xlsx |
| 4 | Seminars Taught per Year per Rank | SAVED.xlsx |
| 5 | Faculty Teaching Seminars by Name | SAVED.xlsx |
| 6 | 2025-2026 Enrollment Report | APPLICATION_CURRENT.xlsx |
| 7 | 2024-2025 Enrollment and Evaluations | HOLYGRAIL.xlsx |
| ALL | Combined packet with all PDFs | All above |

> PDF 3 (3D Map) is not included in this generator.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050 in your browser.

## Usage

1. **Upload** one or more spreadsheets (SAVED.xlsx, APPLICATION_CURRENT.xlsx, HOLYGRAIL.xlsx)
2. **Generate** - click the button to create all department packets
3. **Preview** - click any PDF badge or "Preview Combined" to view in-browser
4. **Download** - grab individual department ZIPs or all packets at once

## Spreadsheet Formats

### SAVED.xlsx
Columns: `Professor`, `Rank`, `Department`, followed by academic year columns (e.g., `2014-15`, `2015-16`, ...). Values: `X` (taught), `XX` (multiple sections), `X*` (joint/co-teaching), `X!` (entry rank), `X!!` (higher rank).

### APPLICATION_CURRENT.xlsx
Columns: `Department`, `Sem#`, `Term`, `Title`, `Fname`, `LName`, `Total Appl Count`, `Placed`

### HOLYGRAIL.xlsx
Columns: `DEPT`, `SEM#`, `TERM`, `TITLE`, `FIRST  NAME`, `LAST NAME`, `APPL#`, `ENROLL`, `SEMQ`, `INST Q`
