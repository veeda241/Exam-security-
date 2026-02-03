"""
ExamGuard Pro - Uploads API
Endpoints for screenshot and webcam frame uploads
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import base64
import os
import uuid

from database import get_db
from models.session import ExamSession
from models.analysis import AnalysisResult
from config import SCREENSHOTS_DIR, WEBCAM_DIR, FORBIDDEN_KEYWORDS
from scoring.engine import ScoringEngine

router = APIRouter()


# ==================== Pydantic Models ====================

class ImageUpload(BaseModel):
    session_id: str
    timestamp: int
    image_data: str  # Base64 data URL


class UploadResponse(BaseModel):
    success: bool
    file_id: str
    analysis_triggered: bool
    forbidden_detected: Optional[bool] = None
    detected_keywords: Optional[list] = None
    face_detected: Optional[bool] = None


# ==================== Endpoints ====================

@router.post("/screenshot", response_model=UploadResponse)
async def upload_screenshot(
    upload: ImageUpload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Upload a screenshot for analysis"""
    
    # Save image
    file_id = f"ss_{upload.session_id}_{upload.timestamp}_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(SCREENSHOTS_DIR, f"{file_id}.jpg")
    
    try:
        # Decode base64 image
        image_data = upload.image_data
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Save to file
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
    
    # Trigger OCR analysis in background
    background_tasks.add_task(
        analyze_screenshot,
        upload.session_id,
        file_id,
        file_path,
        db
    )
    
    return UploadResponse(
        success=True,
        file_id=file_id,
        analysis_triggered=True,
    )


@router.post("/webcam", response_model=UploadResponse)
async def upload_webcam_frame(
    upload: ImageUpload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Upload a webcam frame for face detection"""
    
    # Save image
    file_id = f"wc_{upload.session_id}_{upload.timestamp}_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(WEBCAM_DIR, f"{file_id}.jpg")
    
    try:
        # Decode base64 image
        image_data = upload.image_data
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Save to file
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
    
    # Trigger face detection in background
    background_tasks.add_task(
        analyze_webcam_frame,
        upload.session_id,
        file_id,
        file_path,
        db
    )
    
    return UploadResponse(
        success=True,
        file_id=file_id,
        analysis_triggered=True,
    )


# ==================== Background Analysis Tasks ====================

async def analyze_screenshot(session_id: str, file_id: str, file_path: str, db: AsyncSession):
    """Analyze screenshot for forbidden content using OCR"""
    try:
        from services.ocr import ScreenOCR
        
        result = await analyze_screenshot_ocr(file_path)
        
        # Store analysis result
        analysis = AnalysisResult(
            session_id=session_id,
            analysis_type="OCR",
            source_file=file_path,
            detected_text=result.get("text", ""),
            forbidden_keywords_found=result.get("forbidden_keywords", []),
            result_data=result,
            risk_score_added=result.get("risk_score", 0),
        )
        
        # Use a new session for background task
        from database import async_session
        async with async_session() as session:
            session.add(analysis)
            await session.commit()
            
            # Update session scores
            await ScoringEngine.update_session_scores(session_id, session)
        
    except Exception as e:
        print(f"Screenshot analysis error: {e}")


async def analyze_webcam_frame(session_id: str, file_id: str, file_path: str, db: AsyncSession):
    """Analyze webcam frame for face detection, phones, and gaze"""
    try:
        import cv2
        from main import vision_engine, manager
        import json
        
        frame = cv2.imread(file_path)
        if frame is None:
            return

        # Run advanced vision analysis (YOLOv8 + Gaze)
        if vision_engine:
            analysis_results = vision_engine.analyze_frame(frame)
            
            # Record detections in database
            for violation in analysis_results['violations']:
                impact = 0
                if violation == 'PHONE_DETECTED': impact = 40
                elif violation == 'MULTIPLE_PERSONS': impact = 30
                elif violation == 'GAZE_AWAY_LONG': impact = 20
                elif violation == 'FACE_NOT_FOUND': impact = 10
                
                analysis = AnalysisResult(
                    session_id=session_id,
                    analysis_type="LIVE_VISION_ALERT",
                    source_file=file_path,
                    result_data={"violation": violation, **analysis_results},
                    risk_score_added=impact
                )
                
                # Broadcast alert via WebSockets
                alert_packet = {
                    "type": "VIOLATION",
                    "session_id": session_id,
                    "violation": violation,
                    "timestamp": datetime.utcnow().isoformat(),
                    "impact": impact
                }
                await manager.broadcast(json.dumps(alert_packet))

                # Save record
                from database import async_session
                async with async_session() as session:
                    session.add(analysis)
                    await session.commit()
        else:
            # Fallback to simple face detection if engine not loaded
            from services.face_detection import SecureVision
            result = await detect_face(file_path)
            analysis = AnalysisResult(
                session_id=session_id,
                analysis_type="FACE_DETECTION",
                source_file=file_path,
                face_detected=result.get("face_detected", False),
                result_data=result,
                risk_score_added=result.get("risk_score", 0),
            )
            async with async_session() as session:
                session.add(analysis)
                await session.commit()
                
                # Update session scores
                await ScoringEngine.update_session_scores(session_id, session)
        
    except Exception as e:
        print(f"Webcam analysis error: {e}")
