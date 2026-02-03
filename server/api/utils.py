"""
ExamGuard Pro - API Utilities
Shared utility functions for API operations
"""

import base64
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import cv2
import numpy as np


def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())


def generate_file_id(prefix: str, session_id: str, timestamp: int) -> str:
    """Generate unique file ID"""
    return f"{prefix}_{session_id}_{timestamp}_{uuid.uuid4().hex[:8]}"


def decode_base64_image(base64_string: str) -> Optional[np.ndarray]:
    """
    Decode a base64 image string to OpenCV image.
    
    Args:
        base64_string: Base64 encoded image (with or without data URL prefix)
        
    Returns:
        OpenCV image array or None if decoding fails
    """
    if not base64_string:
        return None
    
    try:
        # Remove data URL prefix if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
        
        image_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None


def encode_image_base64(image: np.ndarray, format: str = "jpg") -> str:
    """
    Encode OpenCV image to base64 string.
    
    Args:
        image: OpenCV image array
        format: Image format (jpg, png)
        
    Returns:
        Base64 encoded string
    """
    ext = f".{format}"
    _, buffer = cv2.imencode(ext, image)
    return base64.b64encode(buffer).decode("utf-8")


def save_image(
    image: np.ndarray,
    folder: str,
    prefix: str,
    format: str = "jpg"
) -> tuple[str, str]:
    """
    Save image to disk.
    
    Args:
        image: OpenCV image array
        folder: Destination folder
        prefix: Filename prefix
        format: Image format
        
    Returns:
        Tuple of (filename, full_path)
    """
    filename = f"{prefix}_{uuid.uuid4().hex}.{format}"
    path = os.path.join(folder, filename)
    cv2.imwrite(path, image)
    return filename, path


def calculate_duration_seconds(
    start: datetime,
    end: Optional[datetime] = None
) -> float:
    """Calculate duration in seconds between two timestamps"""
    end = end or datetime.utcnow()
    return (end - start).total_seconds()


def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string"""
    return dt.isoformat() if dt else None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text with suffix if exceeds max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_risk_level(risk_score: float) -> str:
    """
    Determine risk level from risk score.
    
    Args:
        risk_score: Numeric risk score (0-100)
        
    Returns:
        Risk level string: 'safe', 'review', or 'suspicious'
    """
    if risk_score >= 60:
        return "suspicious"
    elif risk_score >= 30:
        return "review"
    return "safe"


def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def calculate_percentage(value: float, total: float) -> float:
    """Calculate percentage safely"""
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


class ResponseBuilder:
    """Helper class for building consistent API responses"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """Build success response"""
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error(message: str, code: str = None, details: Any = None) -> Dict[str, Any]:
        """Build error response"""
        response = {"success": False, "error": message}
        if code:
            response["code"] = code
        if details:
            response["details"] = details
        return response
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        skip: int,
        limit: int
    ) -> Dict[str, Any]:
        """Build paginated response"""
        return {
            "items": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + len(items) < total
            }
        }
