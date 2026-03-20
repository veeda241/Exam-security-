from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class AnalysisResult(BaseModel):
    """AI analysis result record (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    
    # Analysis type: FACE_DETECTION, OCR, TEXT_SIMILARITY, ANOMALY
    analysis_type: str
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Source reference (screenshot or webcam frame path)
    source_file: Optional[str] = None
    # The URL the student was viewing (for DOM/html2canvas captures)
    source_url: Optional[str] = None
    
    # Results
    result_data: Optional[Any] = None
    
    # Face detection specific
    face_detected: Optional[bool] = None
    face_confidence: Optional[float] = None
    
    # OCR specific
    detected_text: Optional[str] = None
    forbidden_keywords_found: Optional[Any] = None
    
    # Similarity specific
    similarity_score: Optional[float] = None
    matched_content: Optional[str] = None
    
    # Risk contribution
    risk_score_added: float = 0.0
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        data = self.model_dump()
        if data["timestamp"] and hasattr(data["timestamp"], "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
        # Truncate text for summary response
        if data["detected_text"] and len(data["detected_text"]) > 200:
            data["detected_text"] = data["detected_text"][:200]
        return data
