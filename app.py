"""FYS Packet Creator - Flask web application.

Upload spreadsheets, generate PDF packets for all departments,
preview results, and download organized output.
"""

import os
import shutil
import zipfile
import tempfile
import traceback
import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import pandas as pd

from generators.shared import ACRONYM_TO_FULL, sanitize_department_name
from generators.pdf1_seminar_counts import create_pdf1
from generators.pdf2_faculty_rank import create_pdf2, compute_faculty_rank_data
from generators.pdf3_graph import create_pdf3
from generators.pdf4_rank_aggregator import create_pdf4, read_excel_data_by_department
from generators.pdf5_faculty_table import create_pdf5
from generators.pdf5_faculty_table import read_excel_data_by_department as read_pdf5_data
from generators.pdf6_enrollment import create_pdf6, load_enrollment_data, get_all_departments as get_pdf6_depts
from generators.pdf7_evaluations import create_pdf7, load_holygrail_data, get_all_departments as get_pdf7_depts
from generators.combiner import combine_department_pdfs

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

# The notes file written next to the packets. Whoever runs this is pointed at it
# on screen when the run finishes; it is the record of what was produced, what
# was left out on purpose, and what has to change next year.
NOTES_FILENAME = 'README.txt'

# The three source workbooks, in the order they appear on the page. Each entry:
# the upload field, the file name staff know it by, the pages it feeds, and what
# it is. Used both for saving uploads and for the "source files" section of the
# notes, so the two can never disagree about what is required.
SOURCES = [
    ('saved_xlsx', 'SAVED.xlsx', 'pages 1, 2, 3, 4, 5',
     'master faculty teaching history'),
    ('current_seminars_xlsx', 'CURRENT SEMINARS OFFERED.xlsx', 'page 6',
     'seminars running this year, with applications and placements'),
    ('holygrail_xlsx', 'HOLYGRAIL.xlsx', 'page 7',
     "last year's enrollment with Q report scores"),
]

# The current-seminars workbook was called APPLICATION_CURRENT until August
# 2026. Accept the old upload field and the old saved file name so a cached copy
# of the page, or an uploads folder from before the rename, still works.
LEGACY_FIELDS = {'application_current_xlsx': 'current_seminars_xlsx'}

# Departments that exist in the source data for documentation/accounting but
# should NOT get a packet produced. Recorded in the notes file so it is clear
# the omission is intentional, not a failure.
EXCLUDED_DEPTS = {'Committee on Degrees in Social Studies'}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and store them."""
    uploaded = {}

    fields = {field: field for field, _, _, _ in SOURCES}
    fields.update(LEGACY_FIELDS)

    for field, key in fields.items():
        if field in request.files:
            f = request.files[field]
            if f.filename:
                path = os.path.join(UPLOAD_DIR, key + '.xlsx')
                f.save(path)
                uploaded[key] = f.filename

    return jsonify({'status': 'ok', 'uploaded': uploaded})


def uploaded_path(key):
    """Where an uploaded workbook landed, or None if it was never uploaded."""
    candidates = [key] + [old for old, new in LEGACY_FIELDS.items() if new == key]
    for name in candidates:
        path = os.path.join(UPLOAD_DIR, name + '.xlsx')
        if os.path.exists(path):
            return path
    return None


@app.route('/generate', methods=['POST'])
def generate_packets():
    """Generate all PDF packets from uploaded spreadsheets."""
    # Clean output directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    saved_path = uploaded_path('saved_xlsx')
    current_path = uploaded_path('current_seminars_xlsx')
    holygrail_path = uploaded_path('holygrail_xlsx')

    results = {'departments': [], 'errors': [], 'pdfs_generated': 0}
    all_depts = set()

    # Determine departments from uploaded files
    saved_headers = None
    saved_data_by_dept = None
    faculty_rank_data = None
    if saved_path:
        try:
            saved_headers, saved_data_by_dept = read_excel_data_by_department(saved_path)
            all_depts.update(saved_data_by_dept.keys())
            # PDF 2 is program-wide; compute its rank breakdown once from every
            # department's rows so each year (incl. the newest) is data-driven.
            all_saved_rows = [row for rows in saved_data_by_dept.values() for row in rows]
            faculty_rank_data = compute_faculty_rank_data(all_saved_rows)
        except Exception as e:
            results['errors'].append(f"Error reading SAVED.xlsx: {str(e)}")

    enrollment_df = None
    if current_path:
        try:
            enrollment_df = load_enrollment_data(current_path)
            all_depts.update(get_pdf6_depts(enrollment_df))
        except Exception as e:
            results['errors'].append(f"Error reading CURRENT SEMINARS OFFERED.xlsx: {str(e)}")

    holygrail_df = None
    if holygrail_path:
        try:
            holygrail_df = load_holygrail_data(holygrail_path)
            all_depts.update(get_pdf7_depts(holygrail_df))
        except Exception as e:
            results['errors'].append(f"Error reading HOLYGRAIL.xlsx: {str(e)}")

    if not all_depts:
        return jsonify({'status': 'error',
                        'message': 'No departments found. Please upload at least one spreadsheet.'})

    # Generate PDFs for each department
    excluded_present = []
    oversized_titles = set()
    # (page number, department) -> the oldest year columns that page left off so
    # its table would fit across the paper. Pages 4 and 5 both do this.
    trimmed_years = {}
    for dept in sorted(all_depts):
        if not dept or dept == 'nan':
            continue

        if dept.strip() in EXCLUDED_DEPTS:
            excluded_present.append(dept.strip())
            continue

        sanitized = sanitize_department_name(dept)
        dept_folder = os.path.join(OUTPUT_DIR, f"[{sanitized}]")
        os.makedirs(dept_folder, exist_ok=True)

        dept_pdfs = []

        # PDF 1 & 2 (same for all departments - from SAVED.xlsx department list)
        if saved_data_by_dept and dept in saved_data_by_dept:
            try:
                pdf1_path = os.path.join(dept_folder, f"1. [{sanitized}] # of First-Year Seminars by Academic Year.pdf")
                create_pdf1(dept, pdf1_path)
                dept_pdfs.append('PDF 1')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 1: {str(e)}")

            try:
                pdf2_path = os.path.join(dept_folder, f"2. [{sanitized}] % of Seminars According to Faculty Rank.pdf")
                create_pdf2(dept, pdf2_path, faculty_rank_data)
                dept_pdfs.append('PDF 2')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 2: {str(e)}")

        # PDF 3 (3D graph of seminars per year - from SAVED.xlsx)
        if saved_data_by_dept and dept in saved_data_by_dept:
            try:
                pdf3_path = os.path.join(dept_folder, f"3. [{sanitized}] Seminars Taught per Year (3D Graph).pdf")
                create_pdf3(dept, pdf3_path, saved_data_by_dept[dept])
                dept_pdfs.append('PDF 3')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 3: {str(e)}")

        # PDF 4 (Rank Aggregator - from SAVED.xlsx)
        if saved_data_by_dept and dept in saved_data_by_dept:
            try:
                pdf4_path = os.path.join(dept_folder, f"4. [{sanitized}] Seminars Taught per Year per Rank.pdf")
                dropped = create_pdf4(dept, pdf4_path, saved_data_by_dept[dept])
                if dropped:
                    trimmed_years[(4, dept)] = dropped
                dept_pdfs.append('PDF 4')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 4: {str(e)}")

        # PDF 5 (Faculty Table - from SAVED.xlsx)
        if saved_data_by_dept and dept in saved_data_by_dept and saved_headers:
            try:
                pdf5_path = os.path.join(dept_folder, f"5. [{sanitized}] Faculty Teaching Seminars by Name.pdf")
                dropped = create_pdf5(dept, pdf5_path, saved_headers, saved_data_by_dept[dept])
                if dropped:
                    trimmed_years[(5, dept)] = dropped
                dept_pdfs.append('PDF 5')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 5: {str(e)}")

        # PDF 6 (Enrollment - from CURRENT SEMINARS OFFERED.xlsx)
        if enrollment_df is not None:
            try:
                pdf6_path = os.path.join(dept_folder, f"6. [{sanitized}] 2026\u20132027 Enrollment Report.pdf")
                oversized_titles.update(create_pdf6(dept, pdf6_path, enrollment_df) or [])
                dept_pdfs.append('PDF 6')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 6: {str(e)}")

        # PDF 7 (Evaluations - from HOLYGRAIL.xlsx)
        if holygrail_df is not None:
            try:
                pdf7_path = os.path.join(dept_folder, f"7. [{sanitized}] 2025\u20132026 Enrollment and Evaluations.pdf")
                oversized_titles.update(create_pdf7(dept, pdf7_path, holygrail_df) or [])
                dept_pdfs.append('PDF 7')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 7: {str(e)}")

        # Combine all PDFs for this department
        if dept_pdfs:
            try:
                combined_path = os.path.join(dept_folder, f"ALL [{sanitized}] Files.pdf")
                combine_department_pdfs(dept_folder, combined_path)
                dept_pdfs.append('Combined')
            except Exception as e:
                results['errors'].append(f"[{dept}] Combine: {str(e)}")

        if dept_pdfs:
            results['departments'].append({
                'name': dept,
                'full_name': ACRONYM_TO_FULL.get(dept, dept),
                'pdfs': dept_pdfs
            })

    # Write a plain-text note so anyone browsing output/ understands what was
    # produced and, importantly, what was intentionally left out. The same text
    # goes back to the browser, so the run cannot finish without it being shown.
    notes = ''
    provided = {'saved_xlsx': saved_path,
                'current_seminars_xlsx': current_path,
                'holygrail_xlsx': holygrail_path}
    missing = [f'{filename} ({pages})' for field, filename, pages, _ in SOURCES
               if not provided.get(field)]
    try:
        produced = [d['name'] for d in results['departments']]
        lines = [
            'FYS PACKET CREATOR. READ THIS BEFORE SENDING THE PACKETS OUT.',
            f'Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}',
            '',
            f'Departments with packets produced: {len(produced)}',
            f'PDFs produced: {results["pdfs_generated"]}',
            '',
            'SOURCE FILES',
            '  All three are needed for a complete packet. Any file left out just',
            '  skips its own pages; the rest of the packet is still produced.',
            '',
        ]
        for field, filename, pages, purpose in SOURCES:
            state = 'used' if provided.get(field) else 'NOT UPLOADED'
            lines += [f'  {filename}',
                      f'      {purpose}',
                      f'      feeds {pages} ({state})']
        if missing:
            lines += ['', '  Missing, so those pages are not in this packet:']
            lines += [f'    - {m}' for m in missing]
        if excluded_present:
            lines += [
                '',
                'Present in the source data but intentionally NOT produced as packets',
                '(kept in the data for documentation/accounting only):',
            ]
            lines += [f'  - {d}' for d in sorted(set(excluded_present))]
        if oversized_titles:
            lines += [
                '',
                'Seminar titles too long to fit on one line even at the smallest',
                'readable size. These wrapped onto a second line. To keep them on one',
                'line, add a shortened form to TITLE_OVERRIDES in generators/shared.py',
                '(cut at the title\'s own colon or dash, do not paraphrase):',
            ]
            lines += [f'  - {t}' for t in sorted(oversized_titles)]
        if trimmed_years:
            lines += [
                '',
                'Tables that start a year later than the others. These departments have',
                'long faculty names, so the full table comes out wider than the paper and',
                'would be cut off at BOTH edges (the first letter of every name and the',
                'newest year column). The oldest year columns were left off instead, so',
                'the year headings stay spelled out the same as every other department.',
                'Nothing else about these pages differs. Years left off:',
            ]
            lines += [f'  - Page {page}, {d}: {", ".join(str(y) for y in years)}'
                      for (page, d), years in sorted(trimmed_years.items())]
        if results['errors']:
            lines += ['', 'Errors during generation:']
            lines += [f'  - {e}' for e in results['errors']]
        # Year-dependent labels that are hardcoded and must be bumped by +1 each
        # cycle. Page 2 is computed from the master and needs no edit. Listed here
        # so whoever runs this next year knows exactly what to change.
        lines += [
            '',
            'THIS PACKET COVERS',
            '  Upcoming year (page 6): 2026-2027   <- applications and enrollment',
            '  Past year (page 7):     2025-2026   <- Q report scores',
            '  Page 6 is always ONE YEAR AHEAD of page 7. If those two ever read the',
            '  same year, one of them was missed in the yearly bump below.',
            '',
            'HEADS UP FOR NEXT YEAR (every date below shifts +1):',
            '  These are hardcoded and NOT auto-derived. For the 2027-2028 packet,',
            '  change each one to the year shown in the "next cycle" column:',
            '',
            '                              this cycle        next cycle',
            '  - Page 1 chart              26-27 = 116       add 27-28 = <count>',
            '      generators/pdf1_seminar_counts.py (DEFAULT_YEARS and DEFAULT_COUNTS).',
            '      Append the new year and its seminar count; do not replace 26-27.',
            '  - Page 6 title + filename   2026-2027         2027-2028',
            '      generators/pdf6_enrollment.py ("2026–2027 Enrollment Report") and the',
            '      pdf6_path filename in app.py. Rebuild its input first with',
            '      tools/build_pdf6_input.py (needs the new FYSEMR enrollment export,',
            '      the seminar catalog, and the updated master).',
            '  - Page 7 title + filename   2025-2026         2026-2027',
            '      generators/pdf7_evaluations.py ("2025–2026 Enrollment and Evaluations")',
            '      and the pdf7_path filename in app.py. Its data is the past-year Q',
            '      report Excel, built from the HCIR dashboard scores.',
            '  - Page 2 (% by rank)        no edit needed',
            '      Computed from the master spreadsheet; it picks up the newest year',
            '      column on its own.',
        ]
        notes = '\n'.join(lines) + '\n'
        with open(os.path.join(OUTPUT_DIR, NOTES_FILENAME), 'w') as fh:
            fh.write(notes)
    except Exception as e:
        results['errors'].append(f'{NOTES_FILENAME}: {str(e)}')

    # A short list of what a person actually has to look at, so the page can say
    # why the notes are worth opening instead of just insisting that they are.
    attention = []
    if missing:
        attention.append(f'{len(missing)} source file{"s" if len(missing) > 1 else ""} '
                         f'not uploaded, so some pages are missing')
    if trimmed_years:
        attention.append(f'{len(trimmed_years)} table{"s" if len(trimmed_years) > 1 else ""} '
                         f'start a year later to fit the page')
    if oversized_titles:
        attention.append(f'{len(oversized_titles)} seminar title'
                         f'{"s" if len(oversized_titles) > 1 else ""} wrapped onto a second line')
    if excluded_present:
        attention.append(f'{len(set(excluded_present))} department'
                         f'{"s" if len(set(excluded_present)) > 1 else ""} left out on purpose')

    results['notes'] = notes
    results['notes_filename'] = NOTES_FILENAME
    results['attention'] = attention
    return jsonify({'status': 'ok', 'results': results})


@app.route('/notes')
def generation_notes():
    """The notes file for the last run, as plain text."""
    path = os.path.join(OUTPUT_DIR, NOTES_FILENAME)
    if not os.path.exists(path):
        return 'No packets have been generated yet.', 404, {'Content-Type': 'text/plain'}
    return send_file(path, mimetype='text/plain')


@app.route('/departments')
def list_departments():
    """List all generated department folders."""
    if not os.path.exists(OUTPUT_DIR):
        return jsonify([])

    departments = []
    for folder in sorted(os.listdir(OUTPUT_DIR)):
        if folder.startswith('[') and folder.endswith(']'):
            dept_code = folder[1:-1]
            dept_path = os.path.join(OUTPUT_DIR, folder)
            pdfs = [f for f in os.listdir(dept_path) if f.endswith('.pdf')]
            departments.append({
                'code': dept_code,
                'full_name': ACRONYM_TO_FULL.get(dept_code, dept_code),
                'folder': folder,
                'pdfs': sorted(pdfs),
            })

    return jsonify(departments)


@app.route('/preview/<dept>/<path:filename>')
def preview_pdf(dept, filename):
    """Serve a PDF file for in-browser preview."""
    dept_folder = os.path.join(OUTPUT_DIR, f"[{dept}]")
    return send_from_directory(dept_folder, filename, mimetype='application/pdf')


@app.route('/download/department/<dept>')
def download_department(dept):
    """Download all PDFs for a department as a zip."""
    dept_folder = os.path.join(OUTPUT_DIR, f"[{dept}]")
    if not os.path.exists(dept_folder):
        return jsonify({'error': 'Department not found'}), 404

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in os.listdir(dept_folder):
            if f.endswith('.pdf'):
                zf.write(os.path.join(dept_folder, f), f"[{dept}]/{f}")

    buf.seek(0)
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name=f"[{dept}]_packets.zip")


@app.route('/download/all')
def download_all():
    """Download all department packets as a single zip."""
    if not os.path.exists(OUTPUT_DIR):
        return jsonify({'error': 'No output generated yet'}), 404

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for f in files:
                if f.endswith('.pdf'):
                    full_path = os.path.join(root, f)
                    arcname = os.path.relpath(full_path, OUTPUT_DIR)
                    zf.write(full_path, arcname)
        # The notes travel with the packets, so whoever opens the zip later
        # still has the record of what was left out and why.
        notes_path = os.path.join(OUTPUT_DIR, NOTES_FILENAME)
        if os.path.exists(notes_path):
            zf.write(notes_path, NOTES_FILENAME)

    buf.seek(0)
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name='FYS_Packets_All.zip')


if __name__ == '__main__':
    app.run(debug=True, port=5050)
