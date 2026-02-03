"""
ExamGuard Pro - Analysis Routes
Endpoints for AI analysis integration and dashboard data
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import base64
import os
import cv2
import numpy as np
import uuid
import json
from datetime import datetime

from database import get_db
from models.session import ExamSession
from models.analysis import AnalysisResult
from models.student import Student
from config import SCREENSHOTS_DIR, WEBCAM_DIR
# from main import vision_engine # Circular dependency
from services.ocr import analyze_screenshot_ocr
from services.similarity import check_text_similarity
from services.llm import get_llm_service
from scoring.engine import ScoringEngine

router = APIRouter()

# Data Models
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    session_id: str
    webcam_image: Optional[str] = None # Base64
    screen_image: Optional[str] = None # Base64
    clipboard_text: Optional[str] = None
    timestamp: int

class DashboardStats(BaseModel):
    total_students: int
    active_sessions: int
    average_engagement: float
    high_risk_count: float

class StudentSummary(BaseModel):
    student_id: str
    name: str
    email: str
    latest_session_id: Optional[str]
    risk_score: float
    engagement_score: float
    effort_alignment: float
    status: str

# Helper to decode image
def decode_image(base64_string):
    if not base64_string:
        return None
    try:
        # Remove header if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
        
        image_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None

def save_image(img, folder, prefix):
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
    path = os.path.join(folder, filename)
    cv2.imwrite(path, img)
    return filename, path

@router.post("/process")
async def process_analysis_data(
    request: Request,
    analysis_request: AnalysisRequest, # Renamed to avoid name collision if any, or just use type hint.
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Process webcam and screen data"""
    
    # Access vision engine from app state
    vision_engine = getattr(request.app.state, "vision_engine", None)
    
    # Verify session
    result = await db.execute(select(ExamSession).where(ExamSession.id == analysis_request.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    analysis_record = AnalysisResult(
        session_id=session.id,
        timestamp=datetime.utcnow(),
        analysis_type="MULTI_MODAL",
        result_data={}
    )
    
    # 1. Webcam Analysis (MediaPipe / YOLO)
    webcam_frame = decode_image(analysis_request.webcam_image)
    if webcam_frame is not None:
        # Save image (optional, maybe subsample)
        fname, fpath = save_image(webcam_frame, WEBCAM_DIR, "webcam")
        analysis_record.source_file = f"/uploads/webcam/{fname}"
        
        # Analyze
        if vision_engine:
            vision_results = vision_engine.analyze_frame(webcam_frame)
            analysis_record.face_detected = "FACE_NOT_FOUND" not in vision_results['violations']
            # Calculate simple engagement confidence from gaze
            # This is a simplification; ideally SecureVision returns a float
            analysis_record.face_confidence = 0.0 if "FACE_NOT_FOUND" in vision_results['violations'] else 0.9
            
            # Update session engagement score
            if "GAZE_AWAY_LONG" in vision_results['violations']:
                session.engagement_score = max(0, session.engagement_score - 5)
            elif "FACE_NOT_FOUND" in vision_results['violations']:
                session.face_absence_count += 1
                session.engagement_score = max(0, session.engagement_score - 10)
            else:
                 session.engagement_score = min(100, session.engagement_score + 1)

            analysis_record.result_data["vision"] = vision_results
            
            # Risk calculation
            analysis_record.risk_score_added += vision_results['integrity_score_impact']

            # 1.5 Object Detection (YOLO)
            # Run on every 5th frame or specific request to save compute? 
            # For MVP, run on every processed frame request (since requests are periodic)
            from services.object_detection import get_object_detector
            yolo = get_object_detector()
            obj_result = yolo.detect(webcam_frame)
            
            if obj_result["forbidden_detected"]:
                analysis_record.result_data["objects"] = obj_result["objects"]
                analysis_record.risk_score_added += obj_result["risk_score"]
                session.risk_score = min(100, session.risk_score + obj_result["risk_score"])

    # 2. Screen Analysis (OCR)
    screen_frame = decode_image(analysis_request.screen_image)
    if screen_frame is not None:
        # Save image
        fname, fpath = save_image(screen_frame, SCREENSHOTS_DIR, "screen")
        
        # Async OCR
        ocr_result = await analyze_screenshot_ocr(fpath)
        
        analysis_record.detected_text = ocr_result.get("text", "")
        analysis_record.forbidden_keywords_found = ocr_result.get("forbidden_keywords", [])
        
        if ocr_result.get("forbidden_detected"):
            session.forbidden_site_count += 1
            session.content_relevance = max(0, session.content_relevance - 20)
            analysis_record.risk_score_added += ocr_result.get("risk_score", 0)
        
        analysis_record.result_data["ocr"] = ocr_result

    # 3. Text Similarity (Clipboard)
    # 3. Text Similarity (Clipboard)
    if analysis_request.clipboard_text:
        sim_result = await check_text_similarity(analysis_request.clipboard_text)
        analysis_record.similarity_score = sim_result.get("similarity_score", 0)
        if sim_result.get("is_suspicious"):
            session.effort_alignment = max(0, session.effort_alignment - 15)
            analysis_record.risk_score_added += sim_result.get("risk_score", 0)
        
        analysis_record.result_data["similarity"] = sim_result

    # 4. Smart Local LLM Analysis (Optional - if Ollama is running)
    llm = get_llm_service()
    if await llm.check_connection():
        llm_result = await llm.analyze_behavior(
            text=analysis_record.detected_text or "",
            violations=analysis_record.forbidden_keywords_found
        )
        if llm_result.get("is_cheating"):
            analysis_record.risk_score_added += 25
            analysis_record.result_data["llm_analysis"] = llm_result


    # Save Analysis Result
    db.add(analysis_record)
    
    # Update Session Risk
    session.risk_score = min(100, session.risk_score + analysis_record.risk_score_added)
    if session.risk_score > 60:
        session.risk_level = "review"
    if session.risk_score > 85:
        session.risk_level = "suspicious"
        
    await db.commit()
    
    return {"status": "processed", "risk_score": session.risk_score}

@router.get("/dashboard", response_model=List[StudentSummary])
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    """Get summarized student data for dashboard"""
    # Simply fetch all students and their latest session stats
    # Optimization: Query could be improved with joins
    
    result = await db.execute(select(Student))
    students = result.scalars().all()
    
    dashboard_data = []
    
    for student in students:
        # Get latest session
        session_result = await db.execute(
            select(ExamSession)
            .where(ExamSession.student_id == student.id)
            .order_by(ExamSession.started_at.desc())
            .limit(1)
        )
        session = session_result.scalar_one_or_none()
        
        if session:
            dashboard_data.append(StudentSummary(
                student_id=student.id,
                name=student.name,
                email=student.email,
                latest_session_id=session.id,
                risk_score=session.risk_score,
                engagement_score=session.engagement_score,
                effort_alignment=session.effort_alignment,
                status=session.risk_level
            ))
        else:
            dashboard_data.append(StudentSummary(
                student_id=student.id,
                name=student.name,
                email=student.email,
                latest_session_id=None,
                risk_score=0,
                engagement_score=0,
                effort_alignment=0,
                status="inactive"
            ))
            
    return dashboard_data

@router.get("/student/{student_id}")
async def get_student_details(student_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed analysis for a specific student"""
    student_res = await db.execute(select(Student).where(Student.id == student_id))
    student = student_res.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Get sessions
    sessions_res = await db.execute(
        select(ExamSession)
        .where(ExamSession.student_id == student_id)
        .order_by(ExamSession.started_at.desc())
    )
    sessions = sessions_res.scalars().all()
    
    return {
        "student": student.to_dict(),
        "sessions": [s.to_dict() for s in sessions]
    }


# =============================================================================
# TRANSFORMER-BASED ANALYSIS ENDPOINTS
# =============================================================================

class TextAnalysisRequest(BaseModel):
    text: str
    compare_texts: Optional[List[str]] = None

class PlagiarismCheckRequest(BaseModel):
    answer_text: str
    reference_texts: List[str]
    threshold: Optional[float] = 0.7

class MultiAnswerRequest(BaseModel):
    answers: List[str]


@router.post("/transformer/similarity")
async def transformer_similarity_check(request: TextAnalysisRequest):
    """
    Check text similarity using Transformer model.
    
    Use for comparing student answers against reference materials.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    if not request.compare_texts:
        return {
            "error": "No comparison texts provided",
            "status": analyzer.get_status()
        }
    
    results = []
    for compare_text in request.compare_texts:
        result = analyzer.compute_similarity(request.text, compare_text)
        results.append({
            "compare_text_preview": compare_text[:100] + "..." if len(compare_text) > 100 else compare_text,
            **result
        })
    
    # Find max similarity
    max_sim = max(r.get("similarity", 0) for r in results)
    
    return {
        "results": results,
        "max_similarity": round(max_sim, 4),
        "is_suspicious": max_sim > 0.7,
        "analyzer_status": analyzer.get_status()
    }


@router.post("/transformer/plagiarism")
async def transformer_plagiarism_check(request: PlagiarismCheckRequest):
    """
    Check for potential plagiarism in student answer.
    
    Compares answer against known reference texts.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    result = analyzer.check_plagiarism(
        request.answer_text,
        request.reference_texts,
        request.threshold
    )
    
    return {
        **result,
        "analyzer_status": analyzer.get_status()
    }


@router.post("/transformer/cross-compare")
async def transformer_cross_compare(request: MultiAnswerRequest):
    """
    Compare multiple student answers to detect potential copying.
    
    Useful for detecting collusion between students.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    if len(request.answers) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 answers required for comparison"
        )
    
    result = analyzer.analyze_answer_patterns(request.answers)
    
    return {
        **result,
        "analyzer_status": analyzer.get_status()
    }


@router.get("/transformer/status")
async def transformer_status():
    """Get Transformer analyzer status."""
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    return analyzer.get_status()

