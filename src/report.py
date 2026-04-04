# ================================================
# PDF Audit Report Generator
# Exports query history as a signed PDF
# ================================================

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)


def generate_audit_report(queries, documents):
    """
    Generate a PDF audit report from query history.

    Args:
        queries  : list of dicts from recent_queries
        documents: list of dicts from get_all_active_documents

    Returns:
        bytes — PDF file content ready for download
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#16213e"),
        spaceBefore=10,
        spaceAfter=4
    )
    normal_style = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontSize=9,
        leading=13
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#555555")
    )

    story = []
    now = datetime.now().strftime("%B %d, %Y at %H:%M")

    # ── Header ──────────────────────────────────────
    story.append(Paragraph("🛡️ PolicyGuard", title_style))
    story.append(Paragraph("HR Compliance Audit Report", heading_style))
    story.append(Paragraph(f"Generated: {now}", small_style))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 6 * mm))

    # ── Summary ─────────────────────────────────────
    story.append(Paragraph("Summary", heading_style))
    total   = len(queries)
    answers = sum(1 for q in queries if q.get("decision") == "ANSWER")
    refused = sum(1 for q in queries if q.get("decision") == "REFUSED")
    flags   = sum(1 for q in queries if q.get("decision") == "FLAG_CONFLICT")

    summary_data = [
        ["Metric", "Value"],
        ["Total Queries",        str(total)],
        ["Answered",             str(answers)],
        ["Refused (low evidence)", str(refused)],
        ["Conflicts Flagged",    str(flags)],
        ["Documents Loaded",     str(len(documents))],
    ]
    summary_table = Table(summary_data, colWidths=[90 * mm, 60 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",   (0, 0), (-1, 0), 10),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f0f0f0")]),
        ("GRID",    (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    # ── Loaded Documents ────────────────────────────
    if documents:
        story.append(Paragraph("Loaded Policy Documents", heading_style))
        doc_data = [["Filename", "Version", "Pages", "Uploaded"]]
        for d in documents:
            doc_data.append([
                d.get("filename", ""),
                f"v{d.get('version', 1)}",
                str(d.get("pages", "")),
                str(d.get("uploaded", ""))[:10]
            ])
        doc_table = Table(
            doc_data,
            colWidths=[70 * mm, 20 * mm, 20 * mm, 50 * mm]
        )
        doc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f0f0f0")]),
            ("GRID",    (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(doc_table)
        story.append(Spacer(1, 6 * mm))

    # ── Query Log ───────────────────────────────────
    if queries:
        story.append(Paragraph("Query Audit Log", heading_style))
        for i, q in enumerate(queries, 1):
            decision = q.get("decision", "")
            decision_colors = {
                "ANSWER":       "#2d6a4f",
                "REFUSED":      "#e76f51",
                "FLAG_CONFLICT":"#c9184a",
                "CLARIFY":      "#457b9d"
            }
            d_color = decision_colors.get(decision, "#333333")

            story.append(Paragraph(
                f"<b>Q{i}.</b> {q.get('question', '')}",
                normal_style
            ))
            story.append(Paragraph(
                f"<font color='{d_color}'><b>{decision}</b></font> "
                f"| Citation: {q.get('citation', 'N/A')} "
                f"| {str(q.get('timestamp', ''))[:16]}",
                small_style
            ))
            story.append(Spacer(1, 3 * mm))

    # ── Footer ──────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "⚠️ This report is for internal HR compliance tracking only. "
        "Not legal advice. Generated by PolicyGuard — local AI, no cloud.",
        small_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
