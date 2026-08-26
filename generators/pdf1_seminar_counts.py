"""PDF 1: # of First-Year Seminars by Academic Year - Bar chart."""

import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart


# Default seminar counts per academic year
DEFAULT_COUNTS = [113, 126, 141, 135, 128, 121, 94, 112, 111, 103, 110, 122, 116]
DEFAULT_YEARS = ['14-15', '15-16', '16-17', '17-18', '18-19', '19-20',
                 '20-21', '21-22', '22-23', '23-24', '24-25', '25-26', '26-27']


def create_seminar_count_chart(counts, years=None):
    """Create a bar chart for seminar counts by academic year."""
    if years is None:
        years = DEFAULT_YEARS

    drawing = Drawing(700, 350)
    chart = VerticalBarChart()
    chart.x = 60
    chart.y = 60
    chart.width = 580
    chart.height = 220
    chart.data = [counts]
    chart.categoryAxis.categoryNames = years
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(counts) + 40 if counts else 160
    chart.valueAxis.valueStep = 20

    chart.categoryAxis.labels.fontSize = 10
    chart.valueAxis.labels.fontSize = 10
    chart.categoryAxis.labels.fontName = 'Helvetica-Bold'
    chart.valueAxis.labels.fontName = 'Helvetica-Bold'
    chart.categoryAxis.labels.angle = 0

    chart.bars[0].fillColor = colors.darkblue
    chart.bars[0].strokeColor = colors.darkblue
    chart.bars[0].strokeWidth = 1

    drawing.add(chart)

    # Overlay crimson red bar for the last year (current year)
    crimson_red = colors.HexColor('#8B0000')
    bar_width = chart.width / len(years)
    last_bar_x = chart.x + (len(years) - 1) * bar_width + bar_width * 0.1
    max_val = chart.valueAxis.valueMax
    last_bar_height = (counts[-1] / max_val) * chart.height
    red_bar = Rect(last_bar_x, chart.y, bar_width * 0.8, last_bar_height,
                   fillColor=crimson_red, strokeColor=crimson_red, strokeWidth=1)
    drawing.add(red_bar)

    # Count labels on top of bars
    for i, (year, count) in enumerate(zip(years, counts)):
        bar_center_x = chart.x + (i * bar_width) + (bar_width / 2)
        bar_height = (count / max_val) * chart.height
        label_y = chart.y + bar_height + 8
        label_color = crimson_red if i == len(years) - 1 else colors.darkblue
        count_label = String(bar_center_x, label_y, str(count),
                             fontSize=9, fillColor=label_color,
                             fontName='Helvetica-Bold', textAnchor='middle')
        drawing.add(count_label)

    # X-axis label
    x_label = String(350, 30, "Academic Years",
                     fontSize=11, fillColor=colors.black,
                     fontName='Helvetica-Bold', textAnchor='middle')
    drawing.add(x_label)

    # Legend
    legend_x, legend_y = 500, 300
    drawing.add(Rect(legend_x, legend_y, 20, 12,
                     fillColor=colors.darkblue, strokeColor=colors.darkblue))
    drawing.add(String(legend_x + 25, legend_y + 3, "Historical Years",
                       fontSize=10, fillColor=colors.black, fontName='Helvetica'))
    drawing.add(Rect(legend_x, legend_y - 20, 20, 12,
                     fillColor=crimson_red, strokeColor=crimson_red))
    last_year = years[-1].replace('-', '\u2013') if years else ''
    current_label = f"Current Year ({last_year})" if years else "Current Year"
    drawing.add(String(legend_x + 25, legend_y - 17, current_label,
                       fontSize=10, fillColor=colors.black, fontName='Helvetica'))

    return drawing


def create_pdf1(dept, output_path, counts=None, years=None):
    """Create PDF 1 for a specific department."""
    if counts is None:
        counts = DEFAULT_COUNTS

    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
    styles = getSampleStyleSheet()

    mini_title_style = ParagraphStyle(
        'MiniTitle', parent=styles['Heading2'],
        fontSize=14, spaceAfter=5, alignment=1,
        textColor=colors.HexColor('#8B0000'), fontName='Helvetica-Bold'
    )
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, spaceAfter=15, alignment=1,
        textColor=colors.black, fontName='Helvetica-Bold'
    )
    note_style = ParagraphStyle(
        'CustomNote', parent=styles['Normal'],
        fontSize=10, spaceAfter=5, alignment=0,
        textColor=colors.darkgrey, fontName='Helvetica'
    )

    story = [
        Paragraph("FYSP's Evolution", mini_title_style),
        Paragraph("Number of First-Year Seminars by Academic Year", title_style),
        create_seminar_count_chart(counts, years),
        Spacer(1, 10),
        Paragraph("Note: Seminars without enrollments are excluded from analysis", note_style),
    ]

    doc.build(story)
