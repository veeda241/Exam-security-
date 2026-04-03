"""
ExamGuard Pro - Report Generator (Redesigned)
Generates polished PDF reports for exam sessions using ReportLab.
"""

import os
from datetime import datetime
from typing import List

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether, BaseDocTemplate, PageTemplate, Frame
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas as pdfgen_canvas
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] ReportLab not installed. PDF generation will be limited.")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Brand palette ────────────────────────────────────────────────────────────
C_PRIMARY      = colors.HexColor("#4f46e5")   # Indigo
C_PRIMARY_DARK = colors.HexColor("#3730a3")
C_ACCENT       = colors.HexColor("#06b6d4")   # Cyan
C_BG_LIGHT     = colors.HexColor("#f8fafc")
C_BG_MID       = colors.HexColor("#f1f5f9")
C_BORDER       = colors.HexColor("#e2e8f0")
C_TEXT_DARK    = colors.HexColor("#0f172a")
C_TEXT_MID     = colors.HexColor("#475569")
C_TEXT_LIGHT   = colors.HexColor("#94a3b8")
C_WHITE        = colors.white

C_RISK_LOW     = colors.HexColor("#22c55e")   # Green
C_RISK_REVIEW  = colors.HexColor("#f59e0b")   # Amber
C_RISK_HIGH    = colors.HexColor("#ef4444")   # Red

C_SCORE_FILL   = colors.HexColor("#4f46e5")
C_SCORE_BG     = colors.HexColor("#e0e7ff")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


# ── Helper utilities ──────────────────────────────────────────────────────────

def format_date(dt_str: str) -> str:
    if not dt_str:
        return "N/A"
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%d %b %Y  %H:%M:%S UTC")
    except Exception:
        return str(dt_str)


def risk_color(level: str) -> colors.Color:
    lvl = (level or "low").lower()
    if lvl in ("suspicious", "high"):
        return C_RISK_HIGH
    if lvl == "review":
        return C_RISK_REVIEW
    return C_RISK_LOW


def risk_badge_text(level: str) -> str:
    return (level or "low").upper()


def score_bar_drawing(score: float, width: float = 140, height: float = 10) -> Drawing:
    """Returns a small horizontal bar showing a 0-100 score."""
    score = max(0.0, min(100.0, float(score)))
    d = Drawing(width, height)
    # background track
    d.add(Rect(0, 0, width, height, rx=4, ry=4,
               fillColor=C_SCORE_BG, strokeColor=None))
    # filled portion
    fill_w = width * score / 100
    if fill_w > 0:
        d.add(Rect(0, 0, fill_w, height, rx=4, ry=4,
                   fillColor=C_SCORE_FILL, strokeColor=None))
    return d


# ── Page header / footer via canvas callbacks ─────────────────────────────────

class _PageCanvas:
    """Draws a branded header band and a footer on every page."""

    def __init__(self, student_name: str, exam_id: str):
        self.student_name = student_name
        self.exam_id = exam_id

    def __call__(self, canv: pdfgen_canvas.Canvas, doc):
        canv.saveState()
        w, h = A4

        # ── Top header band ──────────────────────────────────────────────────
        band_h = 14 * mm
        canv.setFillColor(C_PRIMARY)
        canv.rect(0, h - band_h, w, band_h, fill=1, stroke=0)

        # Logo / product name
        canv.setFillColor(C_WHITE)
        canv.setFont("Helvetica-Bold", 12)
        canv.drawString(MARGIN, h - band_h + 4 * mm, "ExamGuard Pro")

        # Subtitle on same band
        canv.setFont("Helvetica", 9)
        canv.setFillColor(colors.HexColor("#a5b4fc"))
        canv.drawString(MARGIN + 85, h - band_h + 4 * mm, "Proctoring Report")

        # Right side: page number
        canv.setFillColor(C_WHITE)
        canv.setFont("Helvetica", 8)
        page_label = f"Page {doc.page}"
        canv.drawRightString(w - MARGIN, h - band_h + 4 * mm, page_label)

        # ── Thin accent stripe under header ──────────────────────────────────
        canv.setFillColor(C_ACCENT)
        canv.rect(0, h - band_h - 1.5 * mm, w, 1.5 * mm, fill=1, stroke=0)

        # ── Footer ───────────────────────────────────────────────────────────
        footer_y = 8 * mm
        canv.setStrokeColor(C_BORDER)
        canv.setLineWidth(0.5)
        canv.line(MARGIN, footer_y + 4 * mm, w - MARGIN, footer_y + 4 * mm)

        canv.setFont("Helvetica", 7.5)
        canv.setFillColor(C_TEXT_LIGHT)
        generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        canv.drawString(MARGIN, footer_y, f"Generated: {generated}  |  Student: {self.student_name}  |  Exam: {self.exam_id}")
        canv.drawRightString(w - MARGIN, footer_y, "Confidential – For authorised use only")

        canv.restoreState()


# ── Style factory ─────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["section_title"] = ParagraphStyle(
        "SectionTitle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=C_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
    )
    styles["label"] = ParagraphStyle(
        "Label",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=C_TEXT_MID,
    )
    styles["value"] = ParagraphStyle(
        "Value",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=C_TEXT_DARK,
    )
    styles["small_grey"] = ParagraphStyle(
        "SmallGrey",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=C_TEXT_LIGHT,
    )
    styles["tag_text"] = ParagraphStyle(
        "TagText",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=C_WHITE,
        alignment=TA_CENTER,
    )
    return styles


# ── Section helpers ───────────────────────────────────────────────────────────

def _section_rule(title: str, styles) -> list:
    """Returns a section title + horizontal rule."""
    return [
        Paragraph(title.upper(), styles["section_title"]),
        HRFlowable(width="100%", thickness=0.6, color=C_BORDER, spaceAfter=8),
    ]


def _info_table(rows: list, col_widths=None) -> Table:
    """Two-column key/value table."""
    if col_widths is None:
        col_widths = [45 * mm, 110 * mm]
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), C_BG_MID),
        ("BACKGROUND", (1, 0), (1, -1), C_WHITE),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), C_TEXT_MID),
        ("TEXTCOLOR",  (1, 0), (1, -1), C_TEXT_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_BG_MID, C_BG_LIGHT]),
    ]))
    return t


def _kpi_card_table(cards: list) -> Table:
    """
    Horizontal row of KPI "cards".
    cards = [{"label": str, "value": str, "sub": str, "color": Color}, ...]
    """
    card_w = (PAGE_W - 2 * MARGIN) / len(cards)
    data_row = []
    for c in cards:
        cell = [
            Paragraph(f'<font color="#{c["color"].hexval()[2:]}"><b>{c["value"]}</b></font>',
                      ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=20,
                                     textColor=c["color"], alignment=TA_CENTER)),
            Paragraph(c["label"],
                      ParagraphStyle("kl", fontName="Helvetica-Bold", fontSize=8,
                                     textColor=C_TEXT_MID, alignment=TA_CENTER,
                                     spaceBefore=2)),
        ]
        if c.get("sub"):
            cell.append(Paragraph(c["sub"],
                                  ParagraphStyle("ks", fontName="Helvetica", fontSize=7,
                                                 textColor=C_TEXT_LIGHT, alignment=TA_CENTER)))
        data_row.append(cell)

    t = Table([data_row], colWidths=[card_w] * len(cards))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_WHITE),
        ("BOX",        (0, 0), (-1, -1), 0.4, C_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.4, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _score_metric_table(metrics: list) -> Table:
    """
    metrics = [{"label": str, "score": float}, ...]
    Renders label + percentage text + bar per row.
    """
    rows = []
    for m in metrics:
        score = float(m["score"])
        bar   = score_bar_drawing(score, width=120, height=8)
        rows.append([
            Paragraph(m["label"],
                      ParagraphStyle("ml", fontName="Helvetica", fontSize=9,
                                     textColor=C_TEXT_MID)),
            bar,
            Paragraph(f"<b>{score:.0f}%</b>",
                      ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=C_PRIMARY, alignment=TA_RIGHT)),
        ])

    t = Table(rows, colWidths=[70 * mm, 40 * mm, 22 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_WHITE, C_BG_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, C_BORDER),
    ]))
    return t


def _event_stats_table(session: dict) -> Table:
    header = [
        Paragraph("Event Type",   ParagraphStyle("eh", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE)),
        Paragraph("Count",         ParagraphStyle("eh", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
        Paragraph("Risk Weight",   ParagraphStyle("eh", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
    ]

    def row(label, count_key, weight):
        count = int(session.get(count_key, 0))
        highlight = count > 0
        return [
            Paragraph(label, ParagraphStyle("ec", fontName="Helvetica", fontSize=9,
                                            textColor=C_RISK_HIGH if highlight else C_TEXT_DARK)),
            Paragraph(str(count), ParagraphStyle("en", fontName="Helvetica-Bold", fontSize=9,
                                                 textColor=C_RISK_HIGH if highlight else C_TEXT_DARK,
                                                 alignment=TA_CENTER)),
            Paragraph(weight, ParagraphStyle("ew", fontName="Helvetica", fontSize=9,
                                             textColor=C_TEXT_MID, alignment=TA_CENTER)),
        ]

    data = [
        header,
        row("Tab Switches",    "tab_switch_count",    "+10 pts each"),
        row("Copy / Paste",    "copy_count",           "+15 pts each"),
        row("Face Absences",   "face_absence_count",   "+20 pts each"),
        row("Forbidden Sites", "forbidden_site_count", "+40 pts each"),
        [
            Paragraph("Total Events", ParagraphStyle("ef", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_DARK)),
            Paragraph(str(session.get("total_events", 0)),
                      ParagraphStyle("en", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=C_PRIMARY, alignment=TA_CENTER)),
            Paragraph("—", ParagraphStyle("ew", fontName="Helvetica", fontSize=9,
                                          textColor=C_TEXT_LIGHT, alignment=TA_CENTER)),
        ],
    ]

    col_w = [(PAGE_W - 2 * MARGIN) * r for r in (0.5, 0.2, 0.3)]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [C_WHITE, C_BG_LIGHT]),
        # Total row
        ("BACKGROUND",    (0, -1), (-1, -1), C_BG_MID),
        ("LINEABOVE",     (0, -1), (-1, -1), 1, C_PRIMARY),
        ("GRID",          (0, 0),  (-1, -1), 0.4, C_BORDER),
    ]))
    return t


def _timeline_table(events: list) -> Table:
    """Renders the last 25 events as a styled table."""
    EVENT_COLORS = {
        "tab_switch":    colors.HexColor("#f59e0b"),
        "copy":          colors.HexColor("#8b5cf6"),
        "face_absence":  colors.HexColor("#ef4444"),
        "forbidden_site": colors.HexColor("#dc2626"),
    }

    header = [
        Paragraph("Time",       ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE)),
        Paragraph("Event",      ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE)),
        Paragraph("Details",    ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE)),
    ]
    rows = [header]

    for event in events[-25:]:
        ev_type = event.get("event_type", "unknown")
        dot_color = EVENT_COLORS.get(ev_type, C_TEXT_LIGHT)

        ts = event.get("timestamp", "")
        try:
            time_str = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
        except Exception:
            time_str = str(ts)[:8] or "N/A"

        ev_data = event.get("data") or {}
        if isinstance(ev_data, dict):
            detail = str(ev_data.get("url", ev_data.get("keyword", ev_data.get("detail", ""))))[:55]
        else:
            detail = str(ev_data)[:55]

        rows.append([
            Paragraph(time_str, ParagraphStyle("td", fontName="Helvetica", fontSize=8, textColor=C_TEXT_MID)),
            Paragraph(
                f'<font color="#{dot_color.hexval()[2:]}">&#9679;</font>  {ev_type.replace("_", " ").title()}',
                ParagraphStyle("te", fontName="Helvetica", fontSize=8, textColor=C_TEXT_DARK)
            ),
            Paragraph(detail or "—", ParagraphStyle("tdt", fontName="Helvetica", fontSize=8, textColor=C_TEXT_MID)),
        ])

    col_w = [(PAGE_W - 2 * MARGIN) * r for r in (0.16, 0.30, 0.54)]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ── Risk badge (coloured cell via single-cell Table) ─────────────────────────

def _risk_badge(level: str) -> Table:
    rc = risk_color(level)
    label = risk_badge_text(level)
    t = Table([[Paragraph(label, ParagraphStyle("rb", fontName="Helvetica-Bold", fontSize=9,
                                                textColor=C_WHITE, alignment=TA_CENTER))]],
              colWidths=[30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), rc),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return t


# ── Main report function ──────────────────────────────────────────────────────

async def generate_pdf_report(session: dict, events: List[dict]) -> str:
    if not REPORTLAB_AVAILABLE:
        return await _generate_text_report(session, events)

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(session.get("id", "unknown"))
    filename   = f"report_{session_id[:8]}_{timestamp}.pdf"
    filepath   = os.path.join(REPORTS_DIR, filename)

    styles = _make_styles()

    # Top content margin accounts for the header band + accent stripe
    top_margin    = 16 * mm + 8 * mm   # header band + stripe + breathing room
    bottom_margin = 18 * mm
    frame = Frame(MARGIN, bottom_margin, PAGE_W - 2 * MARGIN, PAGE_H - top_margin - bottom_margin)

    page_cb = _PageCanvas(
        student_name=session.get("student_name", "N/A"),
        exam_id=str(session.get("exam_id", "N/A")),
    )
    template = PageTemplate(id="main", frames=[frame], onPage=page_cb)
    doc = BaseDocTemplate(filepath, pagesize=A4, pageTemplates=[template])

    story = []

    # ── Report title block ───────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Proctoring Session Report",
        ParagraphStyle("ReportTitle", fontName="Helvetica-Bold", fontSize=18,
                       textColor=C_TEXT_DARK, spaceAfter=2),
    ))
    story.append(Paragraph(
        f"Exam ID: {session.get('exam_id', 'N/A')}  &nbsp;|&nbsp;  "
        f"Session: {session_id[:8].upper()}",
        ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=9,
                       textColor=C_TEXT_LIGHT, spaceAfter=10),
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=12))

    # ── KPI cards ────────────────────────────────────────────────────────────
    risk_score = float(session.get("risk_score", 0))
    cards = [
        {"label": "RISK SCORE",   "value": f"{risk_score:.0f}",  "sub": "out of 100",
         "color": risk_color(session.get("risk_level", "low"))},
        {"label": "TAB SWITCHES", "value": str(session.get("tab_switch_count", 0)), "sub": "events",
         "color": C_PRIMARY},
        {"label": "FACE ABSENCES","value": str(session.get("face_absence_count", 0)), "sub": "events",
         "color": C_PRIMARY},
        {"label": "TOTAL EVENTS", "value": str(session.get("total_events", 0)),      "sub": "logged",
         "color": C_ACCENT},
    ]
    story.append(KeepTogether([_kpi_card_table(cards)]))
    story.append(Spacer(1, 8 * mm))

    # ── Session information ───────────────────────────────────────────────────
    story += _section_rule("Session Information", styles)
    ended_str = format_date(session.get("ended_at")) if session.get("ended_at") else "In Progress"
    info_rows = [
        ["Student Name",  session.get("student_name", "N/A")],
        ["Student ID",    session.get("student_id",   "N/A")],
        ["Exam ID",       session.get("exam_id",      "N/A")],
        ["Started At",    format_date(session.get("started_at"))],
        ["Ended At",      ended_str],
    ]
    story.append(_info_table(info_rows))
    story.append(Spacer(1, 6 * mm))

    # ── Risk Assessment ───────────────────────────────────────────────────────
    story += _section_rule("Risk Assessment", styles)

    risk_level = session.get("risk_level", "low")
    risk_row = Table(
        [[
            _risk_badge(risk_level),
            Paragraph(
                f"&nbsp;&nbsp;Risk Score: <b>{risk_score:.1f} / 100</b>",
                ParagraphStyle("rs", fontName="Helvetica", fontSize=11,
                               textColor=C_TEXT_DARK, leading=16),
            ),
        ]],
        colWidths=[35 * mm, PAGE_W - 2 * MARGIN - 35 * mm],
    )
    risk_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(risk_row)
    story.append(Spacer(1, 6 * mm))

    metrics = [
        {"label": "Engagement Score",   "score": session.get("engagement_score",   0)},
        {"label": "Content Relevance",  "score": session.get("content_relevance",  0)},
        {"label": "Effort Alignment",   "score": session.get("effort_alignment",   0)},
    ]
    story.append(_score_metric_table(metrics))
    story.append(Spacer(1, 6 * mm))

    # ── Event Statistics ──────────────────────────────────────────────────────
    story += _section_rule("Event Statistics", styles)
    story.append(_event_stats_table(session))
    story.append(Spacer(1, 6 * mm))

    # ── Event Timeline ────────────────────────────────────────────────────────
    if events:
        story += _section_rule(f"Event Timeline  (last {min(25, len(events))} events)", styles)
        story.append(_timeline_table(events))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    return filepath


# ── Fallback plain-text report ────────────────────────────────────────────────

async def _generate_text_report(session: dict, events: List[dict]) -> str:
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(session.get("id", "unknown"))
    filename   = f"report_{session_id[:8]}_{timestamp}.txt"
    filepath   = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w") as f:
        f.write("=" * 62 + "\n")
        f.write("        EXAMGUARD PRO — PROCTORING REPORT\n")
        f.write("=" * 62 + "\n\n")
        f.write(f"Student Name : {session.get('student_name', 'N/A')}\n")
        f.write(f"Student ID   : {session.get('student_id',   'N/A')}\n")
        f.write(f"Exam ID      : {session.get('exam_id',      'N/A')}\n")
        f.write(f"Started At   : {session.get('started_at',   'N/A')}\n")
        f.write(f"Ended At     : {session.get('ended_at', 'In Progress')}\n\n")
        f.write(f"Risk Score   : {float(session.get('risk_score', 0)):.1f} / 100\n")
        f.write(f"Risk Level   : {str(session.get('risk_level', 'low')).upper()}\n\n")
        f.write(f"Tab Switches : {session.get('tab_switch_count', 0)}\n")
        f.write(f"Copy Events  : {session.get('copy_count', 0)}\n")
        f.write(f"Face Absences: {session.get('face_absence_count', 0)}\n")
        f.write(f"Forbidden    : {session.get('forbidden_site_count', 0)}\n")
        f.write(f"Total Events : {session.get('total_events', 0)}\n\n")
        f.write("=" * 62 + "\n")
        f.write(f"Generated : {datetime.now()}\n")

    return filepath