import os
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def markdown_to_pdf(md_file, pdf_file):
    if not os.path.exists(md_file):
        print(f"File {md_file} not found.")
        return

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    doc = SimpleDocTemplate(pdf_file, pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4F46E5")
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=18,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#1E293B"),
        borderPadding=(0, 0, 5, 0),
        borderWidth=0,
        borderBottomColor=colors.HexColor("#E2E8F0")
    )
    
    h3_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Heading3'],
        fontSize=14,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.HexColor("#334155")
    )
    
    h4_style = ParagraphStyle(
        'SubSubHeader',
        parent=styles['Heading4'],
        fontSize=12,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#475569"),
        fontName='Helvetica-Bold'
    )
    
    body_style = styles['Normal']
    body_style.fontSize = 10
    body_style.leading = 14
    body_style.spaceAfter = 6
    
    code_style = ParagraphStyle(
        'Code',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10,
        backgroundColor=colors.HexColor("#F1F5F9"),
        borderPadding=5
    )
    
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10,
        backgroundColor=colors.HexColor("#FEF3C7"),
        borderPadding=5,
        textColor=colors.HexColor("#92400E")
    )

    story = []
    
    lines = content.split('\n')
    in_code_block = False
    code_lines = []
    
    for line in lines:
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                code_text = "<br/>".join(code_lines)
                story.append(Paragraph(code_text, code_style))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue
            
        # Handle headers
        if line.startswith('# '):
            story.append(Paragraph(line[2:].strip(), title_style))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:].strip(), h2_style))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:].strip(), h3_style))
        elif line.startswith('#### '):
            story.append(Paragraph(line[5:].strip(), h4_style))
        
        # Handle notes/alerts (simplified)
        elif line.startswith('> [!'):
            story.append(Paragraph(line.strip(), note_style))
        elif line.startswith('> '):
            story.append(Paragraph(line[2:].strip(), note_style))
            
        # Handle tables (very simplified)
        elif '|' in line and '-' not in line:
            # Table handling logic here would be complex for multi-line, 
            # so we'll just treat it as text for now or skip header lines
            story.append(Paragraph(line.strip(), body_style))
            
        # Handle list items
        elif line.strip().startswith('- [x]') or line.strip().startswith('- [ ]'):
            text = line.strip()[5:].strip()
            checkbox = "<b>[x]</b> " if "[x]" in line else "<b>[ ]</b> "
            story.append(Paragraph(checkbox + text, body_style))
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            story.append(Paragraph("• " + line.strip()[2:].strip(), body_style))
            
        # Normal text
        elif line.strip():
            # Bold/Italic replacements using regex
            text = line.replace('<', '&lt;').replace('>', '&gt;') # Escape HTML-like chars
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            story.append(Paragraph(text, body_style))
        else:
            story.append(Spacer(1, 6))

    doc.build(story)
    print(f"Successfully created {pdf_file}")

if __name__ == "__main__":
    print("Starting PDF generation script...")
    # Use paths relative to current directory if not found
    md_path = r"C:\Users\Vyas S\.gemini\antigravity\brain\53d72973-20ed-4ef5-9e1d-1498b8f94793\implementation_plan.md"
    print(f"Checking for MD file at: {md_path}")
    if not os.path.exists(md_path):
        print("MD file not found at absolute path, checking relative...")
        # Path for the implementation_plan.md artifact
        md_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", ".gemini", "antigravity", "brain", "53d72973-20ed-4ef5-9e1d-1498b8f94793", "implementation_plan.md")
        print(f"Checking relative path: {md_path}")
        
    # Best guess if above fails: look for common relative path
    if not os.path.exists(md_path):
        md_path = "implementation_plan.md" # Fallback if we are in the artifact dir
        print(f"Checking fallback path: {md_path}")

    pdf_path = os.path.join(os.path.dirname(__file__), "..", "Implementation_Plan.pdf")
    print(f"Target PDF path: {pdf_path}")
    
    if os.path.exists(md_path):
        markdown_to_pdf(md_path, pdf_path)
    else:
        print(f"CRITICAL ERROR: MD file {md_path} not found anywhere.")
