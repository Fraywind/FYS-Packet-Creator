"""PDF 2: % of Seminars According to Faculty Rank - Stacked bar chart."""

import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, String, Line, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart


DEFAULT_FACULTY_RANK_DATA = {
    'Year': ['13-14', '14-15', '15-16', '16-17', '17-18', '18-19',
             '19-20', '20-21', '21-22', '22-23', '23-24', '24-25', '25-26'],
    'Ladder (%)': [77.0, 65.6, 81.0, 81.7, 82.9, 86.7, 90.1, 83.0,
                   86.85, 85.0, 89.0, 85.0, 83.7],
    'Non-Ladder (%)': [23.0, 31.6, 15.0, 15.7, 13.5, 9.4, 7.4, 16.0,
                       11.4, 16.0, 11.0, 14.0, 15.4],
    'Emeritus (%)': [0.0, 2.8, 4.0, 2.6, 3.6, 3.9, 2.5, 1.0,
                     1.75, 1.0, 0.0, 1.0, 1.0],
}


def create_faculty_rank_chart(rank_data=None):
    """Create the faculty rank percentage bar chart."""
    if rank_data is None:
        rank_data = DEFAULT_FACULTY_RANK_DATA

    drawing = Drawing(600, 400)

    bc = VerticalBarChart()
    bc.x = 40
    bc.y = 80
    bc.height = 280
    bc.width = 580

    bc.data = [
        rank_data['Ladder (%)'],
        rank_data['Non-Ladder (%)'],
        rank_data['Emeritus (%)'],
    ]
    bc.categoryAxis.categoryNames = rank_data['Year']
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 20

    try:
        bc.valueAxis.labels.fillColor = colors.white
        bc.valueAxis.labels.fontSize = 0
    except Exception:
        pass

    bc.bars[0].fillColor = colors.HexColor('#8B0000')
    bc.bars[1].fillColor = colors.HexColor('#5A7BC8')
    bc.bars[2].fillColor = colors.HexColor('#808080')

    drawing.add(bc)

    # X-axis label
    graph_center_x = bc.x + (bc.width / 2)
    drawing.add(String(graph_center_x, 50, "Seminar Years",
                       fontSize=10, fillColor=colors.black,
                       fontName='Helvetica-Bold', textAnchor='middle'))

    # Y-axis percentage labels
    for percent in [0, 20, 40, 60, 80, 100]:
        y_pos = bc.y + (percent / 100 * bc.height) - 2
        drawing.add(String(35, y_pos, f"{percent}%",
                           fontSize=8, fillColor=colors.black,
                           fontName='Helvetica-Bold', textAnchor='end'))

    # Legend
    legend_y = 10
    legend_start_x = (600 - 400) / 2 + 90

    drawing.add(Rect(legend_start_x, legend_y - 5, 15, 15,
                     fillColor=colors.HexColor('#8B0000')))
    drawing.add(String(legend_start_x + 25, legend_y, "Ladder",
                       fontSize=12, fillColor=colors.black, fontName='Helvetica'))

    blue_box_start = legend_start_x + 97
    drawing.add(Rect(blue_box_start, legend_y - 5, 15, 15,
                     fillColor=colors.HexColor('#5A7BC8')))
    drawing.add(String(blue_box_start + 25, legend_y, "Non-Ladder",
                       fontSize=12, fillColor=colors.black, fontName='Helvetica'))

    gray_box_start = blue_box_start + 125
    drawing.add(Rect(gray_box_start, legend_y - 5, 15, 15,
                     fillColor=colors.HexColor('#808080')))
    drawing.add(String(gray_box_start + 25, legend_y, "Emeritus",
                       fontSize=12, fillColor=colors.black, fontName='Helvetica'))

    # Data labels above bars
    for i, year in enumerate(rank_data['Year']):
        year_group_width = bc.width / len(rank_data['Year'])
        year_center_x = bc.x + (i * year_group_width) + (year_group_width / 2)
        bar_width = year_group_width / 3

        # Ladder
        ladder_val = rank_data['Ladder (%)'][i]
        if ladder_val > 0:
            y_pos = bc.y + (ladder_val / 100 * bc.height) + 10
            drawing.add(String(year_center_x - bar_width + 7, y_pos,
                               f'{ladder_val:.1f}%', fontSize=8,
                               fillColor=colors.HexColor('#8B0000'),
                               textAnchor='middle'))

        # Non-Ladder
        nl_val = rank_data['Non-Ladder (%)'][i]
        if nl_val > 0:
            y_pos = bc.y + (nl_val / 100 * bc.height) + 10
            offset = 7 if nl_val >= 10.0 else 5
            drawing.add(String(year_center_x + offset, y_pos,
                               f'{nl_val:.1f}%', fontSize=8,
                               fillColor=colors.HexColor('#2E4A8C'),
                               textAnchor='middle'))

        # Emeritus (always show)
        em_val = rank_data['Emeritus (%)'][i]
        y_pos = bc.y + (em_val / 100 * bc.height) + 10
        drawing.add(String(year_center_x + bar_width + 2, y_pos,
                           f'{em_val:.1f}%', fontSize=8,
                           fillColor=colors.HexColor('#808080'),
                           textAnchor='middle'))

    return drawing


def create_pdf2(dept, output_path, rank_data=None):
    """Create PDF 2 for a specific department."""
    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
    styles = getSampleStyleSheet()

    mini_title_style = ParagraphStyle(
        'MiniTitle', parent=styles['Normal'],
        fontSize=12, spaceAfter=-120, alignment=TA_CENTER,
        textColor=colors.HexColor('#8B0000'), fontName='Helvetica-Bold'
    )
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, spaceAfter=5, alignment=TA_CENTER,
        textColor=colors.black, fontName='Helvetica-Bold'
    )

    story = [
        Paragraph("FYSP's Evolution", mini_title_style),
        Paragraph("% of Seminars According to Faculty Rank", title_style),
        Spacer(1, 5),
        create_faculty_rank_chart(rank_data),
    ]

    doc.build(story)
