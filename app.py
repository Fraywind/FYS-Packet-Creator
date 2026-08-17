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

# Departments that exist in the source data for documentation/accounting but
# should NOT get a packet produced. Recorded in output.txt so it is clear the
# omission is intentional, not a failure.
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

    for key in ['saved_xlsx', 'application_current_xlsx', 'holygrail_xlsx']:
        if key in request.files:
            f = request.files[key]
            if f.filename:
                path = os.path.join(UPLOAD_DIR, key + '.xlsx')
                f.save(path)
                uploaded[key] = f.filename

    return jsonify({'status': 'ok', 'uploaded': uploaded})


@app.route('/generate', methods=['POST'])
def generate_packets():
    """Generate all PDF packets from uploaded spreadsheets."""
    # Clean output directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    saved_path = os.path.join(UPLOAD_DIR, 'saved_xlsx.xlsx')
    current_path = os.path.join(UPLOAD_DIR, 'application_current_xlsx.xlsx')
    holygrail_path = os.path.join(UPLOAD_DIR, 'holygrail_xlsx.xlsx')

    results = {'departments': [], 'errors': [], 'pdfs_generated': 0}
    all_depts = set()

    # Determine departments from uploaded files
    saved_headers = None
    saved_data_by_dept = None
    faculty_rank_data = None
    if os.path.exists(saved_path):
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
    if os.path.exists(current_path):
        try:
            enrollment_df = load_enrollment_data(current_path)
            all_depts.update(get_pdf6_depts(enrollment_df))
        except Exception as e:
            results['errors'].append(f"Error reading APPLICATION_CURRENT.xlsx: {str(e)}")

    holygrail_df = None
    if os.path.exists(holygrail_path):
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
    trimmed_page5_years = {}
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
                create_pdf4(dept, pdf4_path, saved_data_by_dept[dept])
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
                    trimmed_page5_years[dept] = dropped
                dept_pdfs.append('PDF 5')
                results['pdfs_generated'] += 1
            except Exception as e:
                results['errors'].append(f"[{dept}] PDF 5: {str(e)}")

        # PDF 6 (Enrollment - from APPLICATION_CURRENT.xlsx)
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
    # produced and, importantly, what was intentionally left out.
    try:
        produced = [d['name'] for d in results['departments']]
        lines = [
            'FYS Packet Creator — generation notes',
            f'Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}',
            '',
            f'Departments with packets produced: {len(produced)}',
        ]
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
        if trimmed_page5_years:
            lines += [
                '',
                'Page 5 tables that start later than the others. These departments have',
                'long faculty names, so the full table comes out wider than the paper and',
                'would be cut at both edges. The earliest year columns were left off so',
                'the year headings stay spelled out in full, the same as every other',
                'department. Years left off:',
            ]
            lines += [f'  - {d}: {", ".join(str(y) for y in years)}'
                      for d, years in sorted(trimmed_page5_years.items())]
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
        with open(os.path.join(OUTPUT_DIR, 'output.txt'), 'w') as fh:
            fh.write('\n'.join(lines) + '\n')
    except Exception as e:
        results['errors'].append(f'output.txt: {str(e)}')

    return jsonify({'status': 'ok', 'results': results})


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

    buf.seek(0)
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name='FYS_Packets_All.zip')


if __name__ == '__main__':
    app.run(debug=True, port=5050)
