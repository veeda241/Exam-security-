"""
ExamGuard Pro - Report Generator
Generates PDF and JSON reports for exam sessions
"""

import os
from datetime import datetime
from typing import List
from config import SCREENSHOTS_DIR, WEBCAM_DIR, RISK_THRESHOLDS

# Try to import ReportLab for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] ReportLab not installed. PDF generation will be limited.")


# Create reports directory
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


async def generate_pdf_report(session: dict, events: List[dict]) -> str:
    """
    Generate a PDF report for an exam session
    
    Args:
        session: ExamSession dictionary (from Supabase)
        events: List of Event dictionaries
        
    Returns:
        Path to generated PDF file
    """
    
    if not REPORTLAB_AVAILABLE:
        return await _generate_text_report(session, events)
    
    # Create PDF filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(session.get("id", "unknown"))
    filename = f"report_{session_id[:8]}_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    # Create document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e293b'),
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#4f46e5'),
    )
    
    normal_style = styles['Normal']
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph("🛡️ ExamGuard Pro", title_style))
    content.append(Paragraph("Proctoring Report", styles['Heading2']))
    content.append(Spacer(1, 20))
    
    # Session Info
    content.append(Paragraph("Session Information", heading_style))
    
    started_at_str = session.get("started_at")
    ended_at_str = session.get("ended_at")
    
    def format_date(dt_str):
        if not dt_str: return "N/A"
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(dt_str)

    session_data = [
        ["Student Name:", str(session.get("student_name", "N/A"))],
        ["Student ID:", str(session.get("student_id", "N/A"))],
        ["Exam ID:", str(session.get("exam_id", "N/A"))],
        ["Started At:", format_date(started_at_str)],
        ["Ended At:", format_date(ended_at_str) if ended_at_str else "In Progress"],
    ]
    
    session_table = Table(session_data, colWidths=[2*inch, 4*inch])
    session_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    content.append(session_table)
    content.append(Spacer(1, 20))
    
    # Risk Score
    content.append(Paragraph("AI Analysis & Risk Assessment", heading_style))
    
    risk_level = session.get("risk_level", "low").lower()
    # Determine risk color
    if risk_level == "suspicious":
        risk_color = colors.HexColor('#ef4444')
    elif risk_level == "review":
        risk_color = colors.HexColor('#f59e0b')
    else:
        risk_color = colors.HexColor('#22c55e')
    
    risk_data = [
        ["Metric", "Score / Value"],
        ["Risk Score:", f"{float(session.get('risk_score', 0)):.1f} / 100"],
        ["Risk Level:", risk_level.upper()],
        ["Engagement Score:", f"{float(session.get('engagement_score', 0)):.1f}%"],
        ["Content Relevance:", f"{float(session.get('content_relevance', 0)):.1f}%"],
        ["Effort Alignment:", f"{float(session.get('effort_alignment', 0)):.1f}%"],
    ]
    
    risk_table = Table(risk_data, colWidths=[2.5*inch, 3.5*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (1, 2), (1, 2), risk_color), # Risk Level coloring
        ('TEXTCOLOR', (1, 2), (1, 2), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    content.append(risk_table)
    content.append(Spacer(1, 20))
    
    # Event Statistics
    content.append(Paragraph("Event Statistics", heading_style))
    
    stats_data = [
        ["Event Type", "Count", "Risk Weight"],
        ["Tab Switches", str(session.get("tab_switch_count", 0)), "+10 each"],
        ["Copy/Paste Events", str(session.get("copy_count", 0)), "+15 each"],
        ["Face Absences", str(session.get("face_absence_count", 0)), "+20 each"],
        ["Forbidden Sites", str(session.get("forbidden_site_count", 0)), "+40 each"],
        ["Total Events", str(session.get("total_events", 0)), "-"],
    ]
    
    stats_table = Table(stats_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    content.append(stats_table)
    content.append(Spacer(1, 20))
    
    # Event Timeline (last 20 events)
    if events:
        content.append(Paragraph("Event Timeline (Recent)", heading_style))
        
        timeline_data = [["Time", "Event Type", "Details"]]
        
        for event in events[-20:]:  # Last 20 events
            ev_ts = event.get("timestamp")
            time_str = "N/A"
            if ev_ts:
                try:
                    time_str = datetime.fromisoformat(ev_ts.replace('Z', '+00:00')).strftime("%H:%M:%S")
                except:
                    time_str = str(ev_ts)
            
            details = ""
            ev_data = event.get("data")
            if ev_data:
                if isinstance(ev_data, dict):
                    details = str(ev_data.get("url", ev_data.get("keyword", "")))[:40]
            
            timeline_data.append([time_str, event.get("event_type", "Unknown"), details])
        
        timeline_table = Table(timeline_data, colWidths=[1.2*inch, 2*inch, 2.8*inch])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        content.append(timeline_table)
    
    # Footer
    content.append(Spacer(1, 40))
    content.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by ExamGuard Pro",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(content)
    
    return filepath


async def _generate_text_report(session: dict, events: List[dict]) -> str:
    """Fallback text report when ReportLab is not available"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(session.get("id", "unknown"))
    filename = f"report_{session_id[:8]}_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("         EXAMGUARD PRO - PROCTORING REPORT\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SESSION INFORMATION\n")
        f.write("-" * 40 + "\n")
        f.write(f"Student Name: {session.get('student_name', 'N/A')}\n")
        f.write(f"Student ID:   {session.get('student_id', 'N/A')}\n")
        f.write(f"Exam ID:      {session.get('exam_id', 'N/A')}\n")
        f.write(f"Started At:   {session.get('started_at', 'N/A')}\n")
        f.write(f"Ended At:     {session.get('ended_at', 'In Progress')}\n\n")
        
        f.write("RISK ASSESSMENT\n")
        f.write("-" * 40 + "\n")
        f.write(f"Risk Score:   {float(session.get('risk_score', 0)):.1f} / 100\n")
        f.write(f"Risk Level:   {str(session.get('risk_level', 'low')).upper()}\n\n")
        
        f.write("EVENT STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Tab Switches:    {session.get('tab_switch_count', 0)}\n")
        f.write(f"Copy Events:     {session.get('copy_count', 0)}\n")
        f.write(f"Face Absences:   {session.get('face_absence_count', 0)}\n")
        f.write(f"Forbidden Sites: {session.get('forbidden_site_count', 0)}\n")
        f.write(f"Total Events:    {session.get('total_events', 0)}\n\n")
        
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now()}\n")
    
    return filepath
