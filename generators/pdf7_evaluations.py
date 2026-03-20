"""PDF 7: Enrollment and Evaluations - Table from HOLYGRAIL.xlsx."""

import os
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .shared import ACRONYM_TO_FULL, sanitize_department_name


def load_holygrail_data(file_path):
    """Load HOLYGRAIL.xlsx and return DataFrame."""
    df = pd.read_excel(file_path)
    return df


def get_department_data(df, department):
    """Get HOLYGRAIL data for a specific department."""
    dept_data = df[df['DEPT'].str.contains(department, case=False, na=False)]
    return dept_data


def get_all_departments(df):
    """Extract all unique departments from HOLYGRAIL data."""
    departments = df['DEPT'].dropna().unique()
    all_depts = set()
    for dept in departments:
        if ' / ' in str(dept):
            parts = [d.strip() for d in str(dept).split(' / ')]
            all_depts.update(parts)
        else:
            all_depts.add(str(dept).strip())
    return sorted([d for d in all_depts if d])


def create_pdf7(department, output_path, df):
    """Create PDF 7 enrollment and evaluations report for a department.

    df: DataFrame from HOLYGRAIL.xlsx
    """
    dept_data = get_department_data(df, department)

    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                 fontSize=20, spaceAfter=10, alignment=TA_CENTER,
                                 fontName='Helvetica-Bold', textColor='darkblue')
    dept_style = ParagraphStyle('DeptSub', parent=styles['Heading2'],
                                fontSize=20, spaceAfter=20, alignment=TA_CENTER,
                                textColor=colors.HexColor('#8B0000'),
                                fontName='Helvetica-Bold')

    story.append(Paragraph("2024\u20132025 Enrollment and Evaluations", title_style))
    full_dept_name = ACRONYM_TO_FULL.get(department, department)
    story.append(Paragraph(full_dept_name, dept_style))
    story.append(Spacer(1, 40))

    if dept_data.empty:
        story.append(Paragraph("No data available for this department.", styles['Normal']))
        doc.build(story)
        return

    # Column mapping
    column_mapping = {}
    for col in dept_data.columns:
        if col in ['SEM#', 'Sem#']:
            column_mapping['Seminar #'] = col
        elif col in ['TITLE', 'Title']:
            column_mapping['Seminar Title'] = col
        elif col in ['TERM', 'Term']:
            column_mapping['Term'] = col
        elif col in ['APPL#', 'Total Appl Count']:
            column_mapping['# of Apps'] = col
        elif col in ['ENROLL ', 'ENROLL', 'Placed']:
            column_mapping['Enrolled'] = col
        elif col in ['SEMQ']:
            column_mapping['Seminar Q'] = col
        elif col in ['INST Q']:
            column_mapping['Instructor Q'] = col

    # Sort by term (Fall before Spring)
    def term_sort_key(term_str):
        t = str(term_str).strip().upper()
        if 'FALL' in t:
            return 0
        elif 'SPRING' in t:
            return 1
        return 2

    data_sorted = dept_data.copy()
    if column_mapping.get('Term', 'TERM') in data_sorted.columns:
        data_sorted['_sort'] = data_sorted[column_mapping.get('Term', 'TERM')].apply(term_sort_key)
        sem_col = column_mapping.get('Seminar #', 'SEM#')
        sort_cols = ['_sort']
        if sem_col in data_sorted.columns:
            sort_cols.append(sem_col)
        data_sorted = data_sorted.sort_values(sort_cols).drop('_sort', axis=1)

    expected_columns = ['Seminar #', 'Seminar Title', 'Professor', 'Term',
                        '# of Apps', 'Enrolled', 'Seminar Q', 'Instructor Q']
    table_data = [expected_columns]
    max_title_length = 0
    max_professor_length = 0

    for _, row in data_sorted.iterrows():
        sem_num = str(row.get(column_mapping.get('Seminar #', 'SEM#'), ''))
        title_text = str(row.get(column_mapping.get('Seminar Title', 'TITLE'), ''))
        max_title_length = max(max_title_length, len(title_text))

        fname = str(row.get('FIRST  NAME', ''))
        lname = str(row.get('LAST NAME', ''))
        professor = f"{fname} {lname}".strip()
        max_professor_length = max(max_professor_length, len(professor))

        term = str(row.get(column_mapping.get('Term', 'TERM'), ''))
        apps = str(row.get(column_mapping.get('# of Apps', 'APPL#'), ''))
        enrolled = str(row.get(column_mapping.get('Enrolled', 'ENROLL '), ''))
        sem_q = str(row.get(column_mapping.get('Seminar Q', 'SEMQ'), ''))
        inst_q = str(row.get(column_mapping.get('Instructor Q', 'INST Q'), ''))

        table_data.append([sem_num, title_text, professor, term, apps, enrolled, sem_q, inst_q])

    table = Table(table_data)

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
        ('FONTSIZE', (0, 1), (0, -1), 10),
        ('FONTSIZE', (2, 1), (-1, -1), 10),
        ('FONTSIZE', (1, 1), (1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])
    table.setStyle(style)

    # Dynamic column widths
    optimal_title = max(2.5, min(5.0, (max_title_length * 0.055) + 0.4))
    optimal_prof = max(1.0, min(2.5, (max_professor_length * 0.07) + 0.25))

    fixed_width = 0.9 + 0.6 + 0.8 + 0.8 + 1.0 + 1.0
    available = 10.2 - fixed_width

    if (optimal_title + optimal_prof) > available:
        if optimal_prof <= available:
            optimal_title = max(2.0, available - optimal_prof)
        else:
            scale = available / (optimal_title + optimal_prof)
            optimal_title = max(2.0, optimal_title * scale)
            optimal_prof = max(1.0, optimal_prof * scale)
    else:
        extra = available - optimal_title - optimal_prof
        optimal_title += extra

    col_widths = [0.9 * inch, optimal_title * inch, optimal_prof * inch,
                  0.6 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch, 1.0 * inch]
    table._argW = col_widths

    story.append(table)
    doc.build(story)
