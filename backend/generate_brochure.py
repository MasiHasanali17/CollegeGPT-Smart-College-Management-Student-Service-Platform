"""
generate_brochure.py

One-off script that generates the downloadable brochure PDF using REAL
data pulled from the existing analytics modules (course fees/duration,
admission steps) so the brochure never contradicts the chatbot or the
website. Run this manually whenever course/fee data changes:

    cd backend
    python generate_brochure.py

This does NOT run automatically on every server start (no need to
regenerate a static PDF on every request) and does not modify any
chatbot files — it only reads from analytics.course / analytics.admission.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from analytics import course as course_analytics
from analytics import admission as admission_analytics


OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "static", "brochure",
    "Parul_University_Brochure.pdf"
)

PURPLE = colors.HexColor("#7c3aed")
DARK = colors.HexColor("#0f172a")
SLATE = colors.HexColor("#64748b")

FEATURED_COURSES = [
    "B.Tech", "MBA", "BBA", "B.Pharm", "B.Arch",
    "BCA", "B.Sc.", "B.Des", "B.Com", "LL.B"
]


def _clean_currency(text):
    """
    reportlab's default Helvetica font has no glyph for ₹, so it renders
    as a solid black box. Swap it for 'Rs.' which renders correctly.
    """
    if not text:
        return text
    return str(text).replace("₹", "Rs.").replace("  ", " ").strip()


def build():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleBig", parent=styles["Title"],
        fontSize=28, textColor=DARK, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=13, textColor=SLATE, spaceAfter=18
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=16, textColor=PURPLE, spaceBefore=18, spaceAfter=10
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=DARK, leading=15
    )
    stat_label_style = ParagraphStyle(
        "StatLabel", parent=styles["Normal"],
        fontSize=9, textColor=SLATE, alignment=1
    )
    stat_value_style = ParagraphStyle(
        "StatValue", parent=styles["Normal"],
        fontSize=16, textColor=PURPLE, alignment=1, spaceAfter=2
    )

    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm
    )

    story = []

    # Header
    story.append(Paragraph("Campus Genius — Parul University", title_style))
    story.append(Paragraph("Official Course & Admission Brochure", subtitle_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=1))

    # Placement highlights (matches the figures shown on the website's Placements page)
    story.append(Paragraph("Placement Highlights", h2_style))

    stat_data = [
        [
            Paragraph("45 LPA", stat_value_style),
            Paragraph("6.5 LPA", stat_value_style),
            Paragraph("2,200+", stat_value_style),
            Paragraph("15k+", stat_value_style),
        ],
        [
            Paragraph("Highest Package", stat_label_style),
            Paragraph("Average Package", stat_label_style),
            Paragraph("Global Recruiters", stat_label_style),
            Paragraph("Students Placed", stat_label_style),
        ],
    ]
    stat_table = Table(stat_data, colWidths=[4.2 * cm] * 4)
    stat_table.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(stat_table)
    story.append(Spacer(1, 10))

    # Featured courses & fees (pulled live from analytics.course)
    story.append(Paragraph("Popular Programs &amp; Tuition Fees", h2_style))

    table_data = [["Course", "Duration", "Tuition Fee (per year)"]]

    for name in FEATURED_COURSES:
        duration = course_analytics.duration(name) or "-"
        fee = _clean_currency(course_analytics.tuition_fee(name)) or "Contact admissions"
        table_data.append([name, duration, fee])

    course_table = Table(table_data, colWidths=[5 * cm, 4 * cm, 7.5 * cm])
    course_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(course_table)
    story.append(Paragraph(
        f"...and {course_analytics.total_courses() - len(FEATURED_COURSES)} more programs across "
        f"{len(course_analytics.faculties())} faculties. Ask Campus AI for the full list.",
        ParagraphStyle("Note", parent=body_style, fontSize=8.5, textColor=SLATE, spaceBefore=6)
    ))

    # Admission process (pulled live from analytics.admission)
    story.append(Paragraph("How to Apply", h2_style))

    steps = admission_analytics.application_steps()
    step_data = [[f"{i+1}.", Paragraph(step, body_style)] for i, step in enumerate(steps)]
    step_table = Table(step_data, colWidths=[1 * cm, 15.5 * cm])
    step_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (0, -1), PURPLE),
        ("FONTSIZE", (0, 0), (0, -1), 10),
    ]))
    story.append(step_table)

    # Contact footer
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=1))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Parul University, Vadodara, Gujarat, India &nbsp;|&nbsp; "
        "+91 98765 43210 &nbsp;|&nbsp; info@paruluniversity.ac.in &nbsp;|&nbsp; "
        "www.paruluniversity.ac.in",
        ParagraphStyle("Footer", parent=body_style, fontSize=9, textColor=SLATE, alignment=1)
    ))
    story.append(Paragraph(
        "Fee figures are indicative and subject to change. Confirm exact figures with "
        "Campus AI or the admissions office before applying.",
        ParagraphStyle("Disclaimer", parent=body_style, fontSize=8, textColor=SLATE,
                        alignment=1, spaceBefore=6)
    ))

    doc.build(story)
    print(f"[Brochure] Generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
