"""PDF 6: 2026-2027 Enrollment Report - Table from FYSP Current Year Seminars.

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
                     fit_seminar_title, TITLE_OVERRIDES, canonical_person_name,
                     marker_for)

# Table cell padding, needed both by the TableStyle and by the title fitting so
# the two agree on how much room a title actually has.
LEFT_PADDING = 4
RIGHT_PADDING = 4

NUMBER_WORDS = {2: 'two', 3: 'three', 4: 'four'}


def load_enrollment_data(file_path):
    """Load FYSP Current Year Seminars and return DataFrame."""
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


def build_co_teacher_index(df, column_mapping):
    """{(sem, term, title): [surname, ...]} for seminars with several teachers.

    Co-teachers sit on separate rows that share a seminar and are often in
    different departments, so this has to be read from the full dataset.
    """
    sem_col = column_mapping.get('Seminar #', 'Sem#')
    title_col = column_mapping.get('Seminar Title', 'Title')
    term_col = column_mapping.get('Term', 'Term')

    index = {}
    for _, row in df.iterrows():
        key = (str(row.get(sem_col, '')), str(row.get(term_col, '')),
               str(row.get(title_col, '')).strip())
        surname = str(row.get('LName', '')).strip()
        if surname and surname not in index.setdefault(key, []):
            index[key].append(surname)
    return {k: v for k, v in index.items() if len(v) > 1}


def create_pdf6(department, output_path, df):
    """Create PDF 6 enrollment report for a department.

    df: DataFrame from FYSP Current Year Seminars
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

    # Co-teachers are separate rows sharing a seminar, and they are often in
    # different departments, so this is read from the whole dataset rather than
    # this department's slice. Each row then credits its counterpart by surname,
    # matching how the past-year Q report writes it.
    co_teachers = build_co_teacher_index(df, column_mapping)

    for _, row in dept_data.iterrows():
        sem_num = str(row.get(column_mapping.get('Seminar #', 'Sem#'), ''))
        title_text = str(row.get(column_mapping.get('Seminar Title', 'Title'), ''))

        lname = str(row.get('LName', '')).strip()
        professor = canonical_person_name(row.get('Fname', ''), lname)
        max_professor_length = max(max_professor_length, len(professor))

        term = str(row.get(column_mapping.get('Term', 'Term'), ''))
        apps = str(row.get(column_mapping.get('# of Apps', 'Total Appl Count'), ''))
        enrolled = str(row.get(column_mapping.get('Enrolled', 'Placed'), ''))

        try:
            sections = int(row.get('Sections', 1) or 1)
        except (TypeError, ValueError):
            sections = 1

        others = [n for n in co_teachers.get((sem_num, term, title_text.strip()), [])
                  if n != lname]
        note = f"Co-teaching with {', '.join(others)}" if others else ''

        raw_rows.append([sem_num, title_text, professor, term, apps, enrolled,
                         sections, note])

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
    footnotes = []          # (glyph, colour, text) in the order they appear

    def next_marker(text):
        # Pinned to 8pt so the marker stays legible even when it rides on a
        # title that had to shrink.
        glyph, colour = marker_for(len(footnotes))
        footnotes.append((glyph, colour, text))
        return f'<font color="{colour}" size="8">{glyph}</font>'

    for (sem_num, title_text, professor, term, apps, enrolled,
         sections, note) in raw_rows:
        text, size, fits, note_shown = fit_seminar_title(
            title_text, title_space, note=note)
        if not fits:
            oversized_titles.append(title_text.strip())
        title_style = ParagraphStyle(f'Title{size}', parent=styles['Normal'],
                                     fontName='Helvetica', fontSize=size,
                                     leading=size + 1.5, alignment=TA_LEFT)
        title_markup = escape(text)

        # The co-teaching credit rides on the title when it fits. When it does
        # not, it moves to a footnote so the title stays readable.
        if note and not note_shown:
            title_markup += ' ' + next_marker(f"{note}.")

        professor_markup = escape(professor)
        # A seminar run as several sections in one term is a single row here,
        # because the registrar reports its applications and enrollment
        # combined. Mark it so the row does not read as a single section.
        if sections > 1:
            count = NUMBER_WORDS.get(sections, sections)
            marker = next_marker(
                f"Prof. {professor.split()[-1]} taught {count} sections of this "
                f"seminar in the same term, counted as {count} seminars in the "
                f"program total. The applications and enrollment shown combine "
                f"all sections.")
            professor_markup = marker + professor_markup

        professor_style = ParagraphStyle('Prof', parent=styles['Normal'],
                                         fontName='Helvetica-Bold', fontSize=10,
                                         leading=12, alignment=TA_LEFT)
        table_data.append([sem_num, Paragraph(title_markup, title_style),
                           Paragraph(professor_markup, professor_style),
                           term, apps, enrolled])

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

    # Footnotes sit above the legend so each marker is explained before the
    # reader reaches the enrollment caveat.
    if footnotes:
        story.append(Spacer(1, 14))
        note_style = ParagraphStyle('Footnote', parent=styles['Normal'],
                                    fontSize=9, alignment=TA_CENTER,
                                    textColor=colors.HexColor('#333333'),
                                    fontName='Helvetica')
        for glyph, colour, text in footnotes:
            story.append(Paragraph(
                f'<font color="{colour}">{glyph}</font> {escape(text)}', note_style))

    # Legend
    story.append(Spacer(1, 20))
    legend_style = ParagraphStyle('RedLegend', parent=styles['Normal'],
                                  fontSize=10, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#8B0000'),
                                  fontName='Helvetica')
    story.append(Paragraph("Enrolled - As of the Fall Course Registration Deadline", legend_style))

    doc.build(story)
    return oversized_titles
