"""PDF 6: 2026-2027 Enrollment Report - Table from APPLICATION_CURRENT.xlsx.

Page 6 reports the UPCOMING academic year, so its year label always reads one
year ahead of page 7. Build its input with tools/build_pdf6_input.py.
"""

import os
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .shared import (ACRONYM_TO_FULL, sanitize_department_name,
                     fit_seminar_title, TITLE_OVERRIDES)

# Table cell padding, needed both by the TableStyle and by the title fitting so
# the two agree on how much room a title actually has.
LEFT_PADDING = 4
RIGHT_PADDING = 4

NUMBER_WORDS = {2: 'two', 3: 'three', 4: 'four'}


def load_enrollment_data(file_path):
    """Load APPLICATION_CURRENT.xlsx and return DataFrame."""
    df = pd.read_excel(file_path)
    return df


def get_department_data(df, department):
    """Get enrollment data for a specific department."""
    dept_data = df[df['Department'].str.contains(department, case=False, na=False)]

    # Remove NO PACKET entries
    if not dept_data.empty:
        mask = ~dept_data.astype(str).apply(
            lambda x: x.str.contains('NO PACKET', case=False, na=False)
        ).any(axis=1)
        dept_data = dept_data[mask]

    return dept_data


def get_all_departments(df):
    """Extract all unique departments, expanding joint departments."""
    departments = df['Department'].dropna().unique()
    departments = [d for d in departments if str(d).strip() and str(d) != '(NO PACKET)']

    all_depts = set()
    for dept in departments:
        if ' / ' in str(dept):
            parts = [d.strip() for d in str(dept).split(' / ')]
            all_depts.update(parts)
        else:
            all_depts.add(str(dept))

    return sorted(all_depts)


def create_pdf6(department, output_path, df):
    """Create PDF 6 enrollment report for a department.

    df: DataFrame from APPLICATION_CURRENT.xlsx
    """
    dept_data = get_department_data(df, department)

    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
    story = []
    styles = getSampleStyleSheet()

    # Department name on top: larger, crimson.
    dept_style = ParagraphStyle('DeptTitle', parent=styles['Heading1'],
                                fontSize=24, spaceAfter=10, alignment=TA_CENTER,
                                textColor=colors.HexColor('#8B0000'),
                                fontName='Helvetica-Bold')
    # Report name below: smaller, black.
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Heading2'],
                                    fontSize=16, spaceAfter=20, alignment=TA_CENTER,
                                    fontName='Helvetica-Bold')

    full_dept_name = ACRONYM_TO_FULL.get(department, department)
    story.append(Paragraph(full_dept_name, dept_style))
    story.append(Paragraph("2026\u20132027 Enrollment Report", subtitle_style))
    story.append(Spacer(1, 40))

    if dept_data.empty:
        story.append(Paragraph("No data available for this department.", styles['Normal']))
        doc.build(story)
        return

    # Column mapping
    column_mapping = {}
    for col in dept_data.columns:
        if col in ['Sem#', 'SEM#']:
            column_mapping['Seminar #'] = col
        elif col in ['Title', 'TITLE']:
            column_mapping['Seminar Title'] = col
        elif col in ['Term', 'TERM']:
            column_mapping['Term'] = col
        elif col in ['Total Appl Count', 'TOTAL APPL COUNT']:
            column_mapping['# of Apps'] = col
        elif col in ['Placed', 'PLACED']:
            column_mapping['Enrolled'] = col

    # Sort by term then seminar number
    if 'Term' in dept_data.columns:
        term_order = {'Fall': 0, 'Spring': 1}
        dept_data = dept_data.copy()
        dept_data['term_sort'] = dept_data['Term'].map(term_order).fillna(2)
        sem_col = column_mapping.get('Seminar #', 'Sem#')
        if sem_col in dept_data.columns:
            dept_data = dept_data.sort_values(['term_sort', sem_col]).drop('term_sort', axis=1)
        else:
            dept_data = dept_data.sort_values(['term_sort']).drop('term_sort', axis=1)

    expected_columns = ['Seminar #', 'Seminar Title', 'Professor', 'Term', '# of Apps', 'Enrolled']
    raw_rows = []
    max_professor_length = 0

    for _, row in dept_data.iterrows():
        sem_num = str(row.get(column_mapping.get('Seminar #', 'Sem#'), ''))
        title_text = str(row.get(column_mapping.get('Seminar Title', 'Title'), ''))

        fname = row.get('Fname', '')
        lname = row.get('LName', '')
        professor = f"{fname} {lname}".strip()
        max_professor_length = max(max_professor_length, len(professor))

        term = str(row.get(column_mapping.get('Term', 'Term'), ''))
        apps = str(row.get(column_mapping.get('# of Apps', 'Total Appl Count'), ''))
        enrolled = str(row.get(column_mapping.get('Enrolled', 'Placed'), ''))

        try:
            sections = int(row.get('Sections', 1) or 1)
        except (TypeError, ValueError):
            sections = 1

        raw_rows.append([sem_num, title_text, professor, term, apps, enrolled, sections])

    # Width is measured against the titles as they will actually print, so a
    # shortened title does not reserve space for its full original length.
    max_title_length = max(
        (len(TITLE_OVERRIDES.get(r[1].strip(), r[1]).strip()) for r in raw_rows),
        default=0)

    # Dynamic column widths
    optimal_title = max(2.5, min(7.0, (max_title_length * 0.05) + 0.5))
    optimal_prof = max(1.2, min(3.2, (max_professor_length * 0.07) + 0.3))

    fixed_width = 0.8 + 0.9 + 0.8 + 0.8
    available = 10.5 - fixed_width

    if (optimal_title + optimal_prof) > available:
        if optimal_title > (available - 1.5):
            optimal_title = available - 1.5
            optimal_prof = 1.5
        else:
            optimal_prof = available - optimal_title
    else:
        extra = available - optimal_title - optimal_prof
        optimal_title += extra

    optimal_title = max(2.5, optimal_title - 0.75)

    col_widths = [0.8 * inch, optimal_title * inch, optimal_prof * inch,
                  0.9 * inch, 0.8 * inch, 0.8 * inch]

    # Titles are Paragraphs rather than plain strings: a plain string does not
    # wrap and prints straight over the Professor column when it is too long.
    # Same rule as PDF 7, shared via fit_seminar_title.
    title_space = (optimal_title * inch) - (LEFT_PADDING + RIGHT_PADDING)
    table_data = [expected_columns]
    oversized_titles = []
    section_notes = []

    for sem_num, title_text, professor, term, apps, enrolled, sections in raw_rows:
        text, size, fits = fit_seminar_title(title_text, title_space)
        if not fits:
            oversized_titles.append(title_text.strip())
        title_style = ParagraphStyle(f'Title{size}', parent=styles['Normal'],
                                     fontName='Helvetica', fontSize=size,
                                     leading=size + 1.5, alignment=TA_LEFT)

        # A seminar run as several sections in one term is a single row here,
        # because the registrar reports its applications and enrollment
        # combined. Mark it so the row does not read as a single section.
        if sections > 1:
            professor = f"*{professor}"
            section_notes.append(
                f"* {professor.lstrip('*')} taught {NUMBER_WORDS.get(sections, sections)} "
                f"sections of this seminar in the same term, counted as "
                f"{NUMBER_WORDS.get(sections, sections)} seminars in the program total. "
                f"The applications and enrollment shown combine all sections.")

        table_data.append([sem_num, Paragraph(escape(text), title_style),
                           professor, term, apps, enrolled])

    table = Table(table_data, colWidths=col_widths)

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        # Column 1 is a Paragraph and carries its own per-row font size.
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), LEFT_PADDING),
        ('RIGHTPADDING', (0, 0), (-1, -1), RIGHT_PADDING),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])
    table.setStyle(style)

    story.append(table)

    # Footnotes sit above the legend so the asterisk is explained before the
    # reader reaches the enrollment caveat.
    if section_notes:
        story.append(Spacer(1, 14))
        note_style = ParagraphStyle('SectionNote', parent=styles['Normal'],
                                    fontSize=9, alignment=TA_CENTER,
                                    textColor=colors.HexColor('#333333'),
                                    fontName='Helvetica')
        for note in section_notes:
            story.append(Paragraph(escape(note), note_style))

    # Legend
    story.append(Spacer(1, 20))
    legend_style = ParagraphStyle('RedLegend', parent=styles['Normal'],
                                  fontSize=10, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#8B0000'),
                                  fontName='Helvetica')
    story.append(Paragraph("Enrolled - As of the Fall Course Registration Deadline", legend_style))

    doc.build(story)
    return oversized_titles
