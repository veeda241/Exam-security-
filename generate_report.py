from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_pdf():
    doc = SimpleDocTemplate("Academic_Hub_Project_Report.pdf", pagesize=LETTER)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor='#6366f1'
    )
    
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor='#4f46e5'
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        spaceAfter=10
    )

    content = []
    
    # Text data from PROJECT_REPORT.md (simplified logic)
    sections = [
        ("Academic Hub: Secure AI Proctoring System", "MainTitle"),
        ("Objective / Problem Statement", "SectionHeader"),
        ("Academic Hub solves the critical problem of remote examination integrity. In an online learning era, preventing cheating—specifically mobile usage and tab-switching—is essential for educators. This project provides a low-cost, high-reliability automated solution.", "BodyText"),
        
        ("Scope & Features", "SectionHeader"),
        ("- Fullscreen Lockdown & UX Interaction Blockers", "BodyText"),
        ("- YOLOv8-powered Cell Phone & Person Detection", "BodyText"),
        ("- MediaPipe Off-Screen Gaze Tracking (>3s rule)", "BodyText"),
        ("- Real-time WebSocket Violation Alerts for Faculty", "BodyText"),
        ("- Comprehensive University Portal with Separate Roles", "BodyText"),
        
        ("Technology Stack", "SectionHeader"),
        ("Frontend: React 18, Vite, Context API", "BodyText"),
        ("Backend: Python, FastAPI, WebSockets", "BodyText"),
        ("AI: YOLOv8, MediaPipe, OpenCV", "BodyText"),
        ("Database: SQLAlchemy, SQLite", "BodyText"),
        
        ("Architecture / Workflow", "SectionHeader"),
        ("1. Student UI enforces Lockdown mode. 2. Captured frames sent to FastAPI. 3. AI Vision engine analyzes behavior. 4. Violations logged to SQLite and broadcasted via WebSockets. 5. Professor Dashboard displays live evidence.", "BodyText"),
        
        ("Impact & Use Cases", "SectionHeader"),
        ("Perfect for Universities, Certification Bodies, and Corporate Training centers requiring high-stakes remote assessment security.", "BodyText"),
        
        ("Future Improvements", "SectionHeader"),
        ("Ongoing development for Audio proctoring and Facial Biometric Identity Verification.", "BodyText"),
    ]

    for text, style_name in sections:
        style = title_style if style_name == "MainTitle" else \
                header_style if style_name == "SectionHeader" else \
                body_style
        content.append(Paragraph(text, style))
        if style_name == "MainTitle":
            content.append(Spacer(1, 12))

    doc.build(content)
    print("PDF generated successfully: Academic_Hub_Project_Report.pdf")

if __name__ == "__main__":
    generate_pdf()
