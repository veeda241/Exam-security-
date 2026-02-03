"""
ExamGuard Pro - Upload Schemas
Pydantic models for file upload requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ImageUpload(BaseModel):
    """Schema for image upload (screenshot or webcam)"""
    session_id: str = Field(..., description="Session identifier")
    timestamp: int = Field(..., description="Client-side timestamp")
    image_data: str = Field(..., description="Base64 encoded image data URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "timestamp": 1706972400000,
                "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            }
        }


class UploadResponse(BaseModel):
    """Schema for upload response"""
    success: bool = True
    file_id: str
    analysis_triggered: bool = False
    forbidden_detected: Optional[bool] = None
    detected_keywords: Optional[List[str]] = None
    face_detected: Optional[bool] = None
    confidence: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "file_id": "ss_session-123_1706972400000_abc123",
                "analysis_triggered": True,
                "forbidden_detected": False,
                "detected_keywords": [],
                "face_detected": True,
                "confidence": 0.95
            }
        }


class BatchUploadRequest(BaseModel):
    """Schema for batch image upload"""
    session_id: str = Field(..., description="Session identifier")
    images: List[ImageUpload] = Field(..., min_length=1, description="List of images to upload")


class BatchUploadResponse(BaseModel):
    """Schema for batch upload response"""
    success: bool = True
    uploaded_count: int = 0
    failed_count: int = 0
    file_ids: List[str] = []
    errors: List[str] = []
