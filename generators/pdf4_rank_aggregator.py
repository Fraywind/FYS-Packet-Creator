"""PDF 4: Seminars Taught per Year per Rank - Aggregated table."""

import os
import openpyxl
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from .shared import ACRONYM_TO_FULL

RANK_CATEGORIES = [
    "Professor & University Professor",
    "Associate Professor",
    "Assistant Professor",
    "SL/SP/PoP/PiR",
    "Emeritus & Emerita",
    "Lecturer",
    "Visiting (all levels)",
]

RANK_ACRONYM_EXPLANATIONS = {
    "SL/SP/PoP/PiR": "Senior Lecturer/Senior Preceptor/Professor of the Practice/Professor in Residence"
}


def categorize_rank(rank):
    """Categorize a rank into one of the predefined categories."""
    if not rank:
        return "Visiting (all levels)"

    original_rank_lower = rank.lower()

    if '/' in rank:
        rank_parts = rank.split('/')
        rank = rank_parts[-1].strip()
        if not rank:
            return "Visiting (all levels)"

    rank_lower = rank.lower()

    if 'visiting' in original_rank_lower:
        return "Visiting (all levels)"
    if 'associate professor' in rank_lower:
        return "Associate Professor"
    if 'assistant professor' in rank_lower:
        return "Assistant Professor"
    if any(kw in rank_lower for kw in ['senior lecturer', 'senior preceptor',
                                        'professor of the practice', 'professor in residence',
                                        'prof. of the practice']):
        return "SL/SP/PoP/PiR"
    if any(kw in rank_lower for kw in ['emeritus', 'emerita']):
        return "Emeritus & Emerita"
    if any(kw in rank_lower for kw in ['lecturer', 'instructor']) and 'senior' not in rank_lower:
        return "Lecturer"
    if 'professor' in rank_lower or rank_lower == 'prof.':
        if not any(kw in rank_lower for kw in ['associate', 'assistant', 'visiting',
                                                'senior lecturer', 'senior preceptor',
                                                'professor of the practice',
                                                'professor in residence',
                                                'emeritus', 'emerita']):
            return "Professor & University Professor"

    return "Visiting (all levels)"


def read_excel_data_by_department(file_path):
    """Read the Excel file and return data grouped by department."""
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    headers = []
    for cell in ws[1]:
        headers.append(str(cell.value) if cell.value else f"Column_{cell.column}")

    data_by_dept = {}
    for row in ws.iter_rows(min_row=2, values_only=False):
        row_data = {}
        for i, cell in enumerate(row):
            if i < len(headers):
                row_data[headers[i]] = cell.value if cell.value is not None else ""

        dept = row_data.get('Department', '')
        if dept:
            data_by_dept.setdefault(dept, []).append(row_data)

    return headers, data_by_dept


def format_number(value):
    """Format numbers consistently: 1.0, 1.5, 2.0, etc."""
    if value == 0:
        return ''
    elif value == int(value):
        return f"{int(value)}.0"
    else:
        return f"{value:.1f}"


def aggregate_by_rank(data):
    """Aggregate teaching data by rank categories."""
    rank_data = {rank: {} for rank in RANK_CATEGORIES}

    year_columns = [k for k in data[0].keys()
                    if str(k).strip().lower() not in ('id', 'department', 'professor', 'rank')]

    abbreviated_year_columns = []
    for year in year_columns:
        if '-' in year:
            parts = year.split('-')
            start = parts[0][-2:] if len(parts[0]) == 4 else parts[0]
            end = parts[1][-2:] if len(parts[1]) == 4 else parts[1]
            abbreviated_year_columns.append(f"{start}-{end}")
        else:
            abbreviated_year_columns.append(year)

    for rank in RANK_CATEGORIES:
        for year in abbreviated_year_columns:
            rank_data[rank][year] = 0

    for row in data:
        rank = row.get('Rank', '')
        rank_text_clean = rank.replace('\n', ' ').replace('\r', ' ').strip() if isinstance(rank, str) else str(rank)
        rank_category = categorize_rank(rank)

        for i, year in enumerate(year_columns):
            value = row.get(year, '')
            abbr_year = abbreviated_year_columns[i]

            # Multi-rank handling
            if '/' in rank_text_clean and value in ('X!', 'X', 'X!!', 'X*!', 'X*'):
                rank_parts = [p.strip() for p in rank_text_clean.split('/')]
                if len(rank_parts) >= 2:
                    first_cat = categorize_rank(rank_parts[0])
                    second_cat = categorize_rank(rank_parts[1]) if len(rank_parts) > 1 else first_cat
                    last_cat = categorize_rank(rank_parts[-1])

                    if value == 'X!':
                        rank_data[first_cat][abbr_year] += 1
                        continue
                    elif value == 'X!!':
                        rank_data[second_cat][abbr_year] += 1
                        continue
                    elif value == 'X*!' or value == 'X*':
                        rank_data[first_cat][abbr_year] += 0.5
                        continue
                    elif value == 'X':
                        rank_data[last_cat][abbr_year] += 1
                        continue

            # Normal aggregation
            if str(value).strip().upper() == 'XXSTAR':
                # Joint appointment teaching two seminars: score 1 for each
                # department row it is joint of. A joint-of-two case adds 1 in
                # each department (2 total program-wide), matching a non-joint
                # two-seminar case ('XX', which scores 2 in its one department).
                rank_data[rank_category][abbr_year] += 1
            elif value == 'X':
                rank_data[rank_category][abbr_year] += 1
            elif value == 'XX':
                rank_data[rank_category][abbr_year] += 2
            elif value in ('X*', 'X**', 'X***', 'X* **'):
                rank_data[rank_category][abbr_year] += 0.5
            elif value in ('X!', 'X!!'):
                rank_data[rank_category][abbr_year] += 1
            elif value == 'X*!':
                rank_data[rank_category][abbr_year] += 0.5

    return rank_data, abbreviated_year_columns


def create_pdf4(dept, output_path, saved_data):
    """Create PDF 4 (Rank Aggregator) for a specific department.

    saved_data: list of row dicts for this department from SAVED.xlsx
    """
    department_full_name = ACRONYM_TO_FULL.get(dept, dept)

    rank_data, year_columns = aggregate_by_rank(saved_data)

    year_totals = {}
    for year in year_columns:
        year_totals[year] = sum(rank_data[rank][year] for rank in RANK_CATEGORIES)

    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Department name on top: larger, crimson.
    dept_style = ParagraphStyle('DeptTitle', parent=styles['Heading1'],
                                fontSize=20, spaceAfter=10, alignment=1,
                                textColor=colors.HexColor('#8B0000'))
    # Report name below: smaller, black.
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Heading2'],
                                    fontSize=16, spaceAfter=20, alignment=1)

    story.append(Paragraph(department_full_name, dept_style))
    story.append(Paragraph("Seminars Taught per Year by Rank", subtitle_style))

    # Build table
    table_data = [['Rank'] + year_columns]
    for rank in RANK_CATEGORIES:
        row = [rank.replace('/', ' ')]
        for year in year_columns:
            row.append(format_number(rank_data[rank][year]))
        table_data.append(row)

    total_row = ['Total'] + [format_number(year_totals[y]) for y in year_columns]
    table_data.append(total_row)

    table = Table(table_data, repeatRows=1)

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 12),
        ('LEFTPADDING', (0, 1), (0, -1), 12),
        ('RIGHTPADDING', (0, 1), (0, -1), 12),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTSIZE', (1, 1), (-1, -1), 12),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (1, 0), (-1, -1), 4),
        ('RIGHTPADDING', (1, 0), (-1, -1), 4),
    ])

    total_idx = len(table_data) - 1
    style.add('BACKGROUND', (0, total_idx), (-1, total_idx), colors.HexColor('#e6e6e6'))
    style.add('FONTNAME', (0, total_idx), (-1, total_idx), 'Helvetica-Bold')
    style.add('FONTSIZE', (0, total_idx), (-1, total_idx), 12)

    table.setStyle(style)
    story.append(table)

    # Legend
    story.append(Spacer(1, 20))
    legend_title_style = ParagraphStyle('LegendTitle', parent=styles['Heading3'],
                                        fontSize=14, spaceAfter=8, alignment=0)
    legend_style = ParagraphStyle('Legend', parent=styles['Normal'],
                                  fontSize=13, spaceAfter=5, leftIndent=20)

    story.append(Paragraph("Legend", legend_title_style))
    story.append(Paragraph("\u2022 Joint Instruction or Co-Teaching = 0.5", legend_style))
    for acronym, full_name in RANK_ACRONYM_EXPLANATIONS.items():
        story.append(Paragraph(f"\u2022 {acronym} = {full_name}", legend_style))

    doc.build(story)
