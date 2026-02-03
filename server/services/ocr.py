"""
ExamGuard Pro - Screen OCR Module
Uses Tesseract for text extraction and forbidden keyword detection
"""

import asyncio
from typing import Dict, Any, List
from config import FORBIDDEN_KEYWORDS, RISK_WEIGHTS

# Try to import Tesseract, fallback if not available
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[WARN] Tesseract not installed. OCR will use fallback mode.")


class ScreenOCR:
    """OCR analysis for screenshots"""
    
    def __init__(self):
        self.forbidden_keywords = [kw.lower() for kw in FORBIDDEN_KEYWORDS]
        # Configure Tesseract path for Windows
        if TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Extract text and check for forbidden keywords"""
        
        if not TESSERACT_AVAILABLE:
            return self._fallback_analysis(image_path)
        
        try:
            # Open image
            image = Image.open(image_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            text_lower = text.lower()
            
            # Find forbidden keywords
            found_keywords = []
            for keyword in self.forbidden_keywords:
                if keyword in text_lower:
                    found_keywords.append(keyword)
            
            # Calculate risk score
            risk_score = 0
            if found_keywords:
                risk_score = RISK_WEIGHTS.get("FORBIDDEN_CONTENT", 40)
                # Add bonus for multiple keywords
                if len(found_keywords) > 1:
                    risk_score += (len(found_keywords) - 1) * 10
            
            return {
                "text": text[:2000],  # Limit text length
                "text_length": len(text),
                "forbidden_keywords": found_keywords,
                "forbidden_detected": len(found_keywords) > 0,
                "risk_score": min(risk_score, 100),
            }
            
        except Exception as e:
            return {
                "text": "",
                "text_length": 0,
                "forbidden_keywords": [],
                "forbidden_detected": False,
                "error": str(e),
                "risk_score": 0,
            }
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback when Tesseract is not available"""
        return {
            "text": "",
            "text_length": 0,
            "forbidden_keywords": [],
            "forbidden_detected": False,
            "warning": "OCR not available - Tesseract not installed",
            "risk_score": 0,
        }


# Global OCR instance
_ocr = None


def get_ocr() -> ScreenOCR:
    """Get or create OCR instance"""
    global _ocr
    if _ocr is None:
        _ocr = ScreenOCR()
    return _ocr


async def analyze_screenshot_ocr(image_path: str) -> Dict[str, Any]:
    """
    Analyze screenshot for text and forbidden keywords (async wrapper)
    
    Args:
        image_path: Path to the screenshot file
        
    Returns:
        Dictionary with OCR results:
        - text: Extracted text (truncated)
        - text_length: Full text length
        - forbidden_keywords: List of found keywords
        - forbidden_detected: bool
        - risk_score: float
    """
    ocr = get_ocr()
    
    # Run OCR in thread pool to not block
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, ocr.analyze, image_path)
    
    return result
