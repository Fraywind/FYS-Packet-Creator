"""PDF 5: Faculty Teaching Seminars by Name - Table with checkmarks."""

import os
import re
import openpyxl
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from .shared import ACRONYM_TO_FULL


def get_rank_full_name(rank):
    """Convert rank to full name and handle stacking."""
    if not rank or str(rank).strip() == '':
        return ''

    rank_normalized = str(rank).replace('/', '\n')
    rank_parts = [p.strip() for p in rank_normalized.split('\n') if p.strip()]

    converted = []
    for part in rank_parts:
        pl = part.lower().strip()
        if 'assistant professor' in pl:
            converted.append('Assistant Professor')
        elif 'associate professor' in pl:
            converted.append('Associate Professor')
        elif 'university professor' in pl:
            converted.append('University Professor')
        elif 'professor of the practice' in pl or 'prof of the practice' in pl:
            converted.append('Professor of the Practice')
        elif 'visiting professor' in pl or 'visiting prof' in pl:
            converted.append('Visiting Professor')
        elif 'professor' in pl and not any(x in pl for x in ['associate', 'assistant', 'emeritus', 'visiting', 'practice', 'university']):
            converted.append('Professor')
        elif 'emeritus' in pl or 'emerita' in pl:
            converted.append('Emeritus')
        elif 'senior lecturer' in pl:
            converted.append('Senior Lecturer')
        elif 'lecturer' in pl:
            converted.append('Lecturer')
        elif 'senior preceptor' in pl:
            converted.append('Senior Preceptor')
        elif 'preceptor' in pl:
            converted.append('Preceptor')
        elif 'visiting' in pl:
            converted.append('Visiting')
        elif part.strip():
            converted.append(part.strip())

    return '\n'.join(converted) if converted else str(rank)


def get_rank_sort_key(rank):
    """Get sorting key for rank hierarchy using the latest/most recent rank."""
    if not rank:
        return 99

    rank_parts = str(rank).replace('/', '\n').split('\n')
    rank_parts = [p.strip() for p in rank_parts if p.strip()]
    if not rank_parts:
        return 99

    latest = rank_parts[-1].lower()

    # Check for Professor/Emeritus combo
    has_prof_emeritus = False
    has_regular_prof = False
    for part in rank_parts:
        pl = part.lower().strip()
        if 'professor' in pl and not any(x in pl for x in ['associate', 'assistant', 'visiting', 'practice', 'university']):
            if any(ep.lower().strip() in ['emeritus', 'emerita'] for ep in rank_parts):
                has_prof_emeritus = True
            else:
                has_regular_prof = True
            break

    if 'university professor' in latest:
        return 0.5
    elif has_prof_emeritus:
        return 5
    elif has_regular_prof:
        return 1
    elif 'associate professor' in latest and 'visiting' not in latest:
        return 2
    elif 'assistant professor' in latest:
        return 3
    elif 'professor of the practice' in latest or 'prof of the practice' in latest:
        return 3.5
    elif 'lecturer' in latest:
        return 4
    elif 'emeritus' in latest or 'emerita' in latest:
        return 5
    elif 'visiting' in latest:
        return 6
    else:
        return 7


def get_rank_abbreviation(rank):
    """Abbreviate Professor of the Practice to P.O.P."""
    if not isinstance(rank, str):
        return str(rank)
    if 'professor of the practice' in rank.lower():
        return 'P.O.P.'
    return rank


def read_excel_data_by_department(file_path):
    """Read SAVED.xlsx and return data grouped by department."""
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


def create_pdf5(dept, output_path, headers, dept_data):
    """Create PDF 5 (Faculty Teaching Seminars by Name) for a department.

    headers: list of column headers from SAVED.xlsx
    dept_data: list of row dicts for this department
    """
    department_full_name = ACRONYM_TO_FULL.get(dept, dept)

    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                            rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                 fontSize=24, spaceAfter=10, alignment=1,
                                 textColor=colors.black)
    dept_style = ParagraphStyle('DeptStyle', parent=styles['Heading2'],
                                fontSize=20, spaceAfter=20, alignment=1,
                                textColor=colors.HexColor('#8B0000'))

    story.append(Paragraph("Faculty Teaching Seminars by Name", title_style))
    story.append(Paragraph(department_full_name, dept_style))

    # Get year columns
    year_columns = [h for h in headers if h not in ['Professor', 'Rank', 'Department']]

    # Sort by rank hierarchy then alphabetically
    def sort_key(row):
        return (get_rank_sort_key(row.get('Rank', '')), str(row.get('Professor', '')).lower())

    sorted_data = sorted(dept_data, key=sort_key)

    # Build table
    table_headers = ['Professor', 'Rank'] + year_columns
    table_data = [table_headers]

    for row in sorted_data:
        table_row = []

        # Professor
        professor = row.get('Professor', '')
        table_row.append(str(professor))

        # Rank
        rank = row.get('Rank', '')
        if rank:
            full_rank = get_rank_full_name(rank)
            abbreviated = get_rank_abbreviation(full_rank)
            # Clean HTML tags if any
            clean = abbreviated.replace('<br/>', '\n').replace('<b>', '').replace('</b>', '')
            table_row.append(clean)
        else:
            table_row.append('')

        # Year columns
        for year in year_columns:
            value = row.get(year, '')
            if value == 'X':
                table_row.append('\u2713')
            elif value == 'XX':
                table_row.append('\u2713\u2713')
            elif value == 'X!':
                table_row.append('\u2713')
            elif value == 'X!!':
                table_row.append('\u2713')
            elif value and isinstance(value, str) and ('X*' in value or (value.startswith('X') and '*' in value)):
                table_row.append('\u25d7')  # Half circle
            else:
                table_row.append(str(value) if value else '')

        table_data.append(table_row)

    table = Table(table_data, repeatRows=1)

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (1, -1), 11),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('FONTSIZE', (2, 1), (-1, -1), 12),
        ('FONTNAME', (2, 1), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    # Color checkmarks
    for row_idx in range(1, len(table_data)):
        for col_idx in range(2, len(table_data[row_idx])):
            cell = table_data[row_idx][col_idx]
            original = sorted_data[row_idx - 1].get(year_columns[col_idx - 2], '')

            if cell == '\u25d7':
                style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx),
                           colors.HexColor('#8B0000'))
            elif cell in ('\u2713', '\u2713\u2713'):
                if original == 'X!':
                    style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.grey)
                elif original == 'X!!':
                    style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx),
                               colors.HexColor('#FF6B6B'))
                else:
                    style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx),
                               colors.HexColor('#8B0000'))

    table.setStyle(style)
    story.append(table)

    # Legend
    story.append(Spacer(1, 20))
    legend_title_style = ParagraphStyle('LegendTitle', parent=styles['Heading3'],
                                        fontSize=16, spaceAfter=10, alignment=0,
                                        textColor=colors.HexColor('#8B0000'))
    legend_style_red = ParagraphStyle('LegendRed', parent=styles['Normal'],
                                      fontSize=13, spaceAfter=5, leftIndent=20,
                                      textColor=colors.HexColor('#8B0000'))
    legend_style_grey = ParagraphStyle('LegendGrey', parent=styles['Normal'],
                                       fontSize=13, spaceAfter=5, leftIndent=20,
                                       textColor=colors.grey)
    legend_style_pink = ParagraphStyle('LegendPink', parent=styles['Normal'],
                                       fontSize=13, spaceAfter=5, leftIndent=20,
                                       textColor=colors.HexColor('#FF6B6B'))

    story.append(Paragraph("Legend:", legend_title_style))
    story.append(Paragraph("\u2713 = Current Rank Years Taught", legend_style_red))
    story.append(Paragraph("\u2713 = FYSP Entry Rank", legend_style_grey))
    story.append(Paragraph("\u2713 = FYSP Higher Rank", legend_style_pink))
    story.append(Paragraph("\u2713\u2713 = Multiple Sections Taught (2.0 score)", legend_style_red))
    story.append(Paragraph("\u25d7 = Joint Department or Co-teaching (0.5 score)", legend_style_red))

    doc.build(story)
