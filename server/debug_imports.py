import sys
print("Python Executable:", sys.executable)
try:
    import numpy as np
    print("✅ numpy version:", np.__version__)
except Exception as e:
    print("❌ numpy error:", e)

try:
    import cv2
    print("✅ cv2 version:", cv2.__version__)
except Exception as e:
    print("❌ cv2 error:", e)

try:
    import mediapipe as mp
    print("✅ mediapipe version:", mp.__version__)
except Exception as e:
    print("❌ mediapipe error:", e)

try:
    import pytesseract
    print("✅ pytesseract imported")
except Exception as e:
    print("❌ pytesseract error:", e)

try:
    from sentence_transformers import SentenceTransformer
    print("✅ sentence-transformers imported")
except Exception as e:
    print("❌ sentence-transformers error:", e)
