from reportlab.pdfgen import canvas
try:
    c = canvas.Canvas(r"c:\hackathon\Gemini_CLI\Exam-security-\test.pdf")
    c.drawString(100, 750, "Hello World")
    c.save()
    print("Success")
except Exception as e:
    print(f"Error: {e}")
