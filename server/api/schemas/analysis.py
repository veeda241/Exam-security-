"""
ExamGuard Pro - Analysis Schemas
Pydantic models for AI analysis requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AnalysisRequest(BaseModel):
    """Schema for multi-modal analysis request"""
    session_id: str = Field(..., description="Session identifier")
    webcam_image: Optional[str] = Field(None, description="Base64 encoded webcam frame")
    screen_image: Optional[str] = Field(None, description="Base64 encoded screenshot")
    clipboard_text: Optional[str] = Field(None, description="Clipboard content for similarity check")
    timestamp: int = Field(..., description="Client-side timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "webcam_image": "data:image/jpeg;base64,/9j/4AAQ...",
                "screen_image": "data:image/png;base64,iVBORw0...",
                "clipboard_text": "Some copied text",
                "timestamp": 1706972400000
            }
        }


class AnalysisResponse(BaseModel):
    """Schema for analysis response"""
    status: str = "processed"
    risk_score: float = 0.0
    face_detected: Optional[bool] = None
    forbidden_detected: Optional[bool] = None
    similarity_score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class TextAnalysisRequest(BaseModel):
    """Schema for Transformer-based text analysis"""
    text: str = Field(..., min_length=1, description="Text to analyze")
    compare_texts: Optional[List[str]] = Field(None, description="Texts to compare against")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "The mitochondria is the powerhouse of the cell.",
                "compare_texts": [
                    "Mitochondria produce ATP for cellular energy.",
                    "The nucleus contains genetic material."
                ]
            }
        }


class PlagiarismCheckRequest(BaseModel):
    """Schema for plagiarism detection request"""
    answer_text: str = Field(..., min_length=1, description="Student's answer to check")
    reference_texts: List[str] = Field(..., min_length=1, description="Reference texts to compare against")
    threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold for flagging")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer_text": "The process of photosynthesis converts light energy to chemical energy.",
                "reference_texts": [
                    "Photosynthesis is the process by which plants convert light into chemical energy.",
                    "Cellular respiration breaks down glucose to produce ATP."
                ],
                "threshold": 0.7
            }
        }


class MultiAnswerRequest(BaseModel):
    """Schema for cross-comparing multiple student answers"""
    answers: List[str] = Field(..., min_length=2, description="List of student answers to compare")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answers": [
                    "Student A's answer about photosynthesis...",
                    "Student B's answer about photosynthesis...",
                    "Student C's answer about photosynthesis..."
                ]
            }
        }


class DashboardStats(BaseModel):
    """Schema for dashboard statistics"""
    total_students: int = 0
    active_sessions: int = 0
    average_engagement: float = 0.0
    high_risk_count: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_students": 150,
                "active_sessions": 45,
                "average_engagement": 87.5,
                "high_risk_count": 3
            }
        }


class TransformerStatusResponse(BaseModel):
    """Schema for Transformer analyzer status"""
    initialized: bool = False
    transformer_available: bool = False
    device: str = "cpu"
    model_loaded: bool = False
