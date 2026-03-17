"""
ExamGuard Pro - Analysis Endpoint
API routes for AI-powered analysis
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
import base64
import os
import cv2
import numpy as np
import uuid

from database import get_db
from models.session import ExamSession
from models.analysis import AnalysisResult
from models.student import Student
from api.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    StudentSummary,
    DashboardStats
)
from config import SCREENSHOTS_DIR, WEBCAM_DIR
from services.ocr import analyze_screenshot_ocr
from services.similarity import check_text_similarity
from services.llm import get_llm_service
from scoring.engine import ScoringEngine

router = APIRouter()


def decode_image(base64_string):
    """Decode base64 image string to OpenCV image"""
    if not base64_string:
        return None
    try:
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
    """Save image to disk and return filename and path"""
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
    path = os.path.join(folder, filename)
    cv2.imwrite(path, img)
    return filename, path


@router.post("/process", response_model=AnalysisResponse)
async def process_analysis_data(
    request: Request,
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Process webcam and screen data for AI analysis"""
    
    # Access vision engine from app state
    vision_engine = getattr(request.app.state, "vision_engine", None)
    
    # Verify session
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == analysis_request.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    analysis_record = AnalysisResult(
        session_id=session.id,
        timestamp=datetime.utcnow(),
        analysis_type="MULTI_MODAL",
        result_data={},
        risk_score_added=0.0,
    )
    
    # 1. Webcam Analysis
    webcam_frame = decode_image(analysis_request.webcam_image)
    if webcam_frame is not None:
        fname, fpath = save_image(webcam_frame, WEBCAM_DIR, "webcam")
        analysis_record.source_file = f"/uploads/webcam/{fname}"
        
        if vision_engine:
            vision_results = vision_engine.analyze_frame(webcam_frame)
            analysis_record.face_detected = "FACE_NOT_FOUND" not in vision_results['violations']
            analysis_record.face_confidence = 0.0 if "FACE_NOT_FOUND" in vision_results['violations'] else 0.9
            
            if "GAZE_AWAY_LONG" in vision_results['violations']:
                session.engagement_score = max(0, session.engagement_score - 5)
            elif "FACE_NOT_FOUND" in vision_results['violations']:
                session.face_absence_count += 1
                session.engagement_score = max(0, session.engagement_score - 10)
            else:
                session.engagement_score = min(100, session.engagement_score + 1)

            analysis_record.result_data["vision"] = vision_results
            analysis_record.risk_score_added += vision_results['integrity_score_impact']

            # Object Detection
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
        fname, fpath = save_image(screen_frame, SCREENSHOTS_DIR, "screen")
        
        ocr_result = await analyze_screenshot_ocr(fpath)
        
        analysis_record.detected_text = ocr_result.get("text", "")
        analysis_record.forbidden_keywords_found = ocr_result.get("forbidden_keywords", [])
        
        if ocr_result.get("forbidden_detected"):
            session.forbidden_site_count += 1
            session.content_relevance = max(0, session.content_relevance - 20)
            analysis_record.risk_score_added += ocr_result.get("risk_score", 0)
        
        analysis_record.result_data["ocr"] = ocr_result

    # 3. Text Similarity (Clipboard)
    if analysis_request.clipboard_text:
        sim_result = await check_text_similarity(analysis_request.clipboard_text)
        analysis_record.similarity_score = sim_result.get("similarity_score", 0)
        if sim_result.get("is_suspicious"):
            session.effort_alignment = max(0, session.effort_alignment - 15)
            analysis_record.risk_score_added += sim_result.get("risk_score", 0)
        
        analysis_record.result_data["similarity"] = sim_result

    # 4. LLM Analysis (Optional)
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
    
    return AnalysisResponse(
        status="processed",
        risk_score=session.risk_score,
        face_detected=analysis_record.face_detected,
        forbidden_detected=len(analysis_record.forbidden_keywords_found) > 0,
        similarity_score=analysis_record.similarity_score
    )


@router.get("/dashboard", response_model=List[StudentSummary])
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    """Get summarized student data for dashboard"""
    
    result = await db.execute(select(Student))
    students = result.scalars().all()
    
    dashboard_data = []
    
    for student in students:
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
                department=student.department,
                year=student.year,
                latest_session_id=session.id,
                risk_score=session.risk_score,
                engagement_score=session.engagement_score,
                effort_alignment=session.effort_alignment,
                content_relevance=session.content_relevance,
                tab_switch_count=session.tab_switch_count,
                forbidden_site_count=session.forbidden_site_count,
                copy_count=session.copy_count,
                status=session.risk_level
            ))
        else:
            dashboard_data.append(StudentSummary(
                student_id=student.id,
                name=student.name,
                email=student.email,
                department=student.department,
                year=student.year,
                latest_session_id=None,
                risk_score=0,
                engagement_score=0,
                effort_alignment=0,
                content_relevance=0,
                tab_switch_count=0,
                forbidden_site_count=0,
                copy_count=0,
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


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overall dashboard statistics"""
    
    # Get counts
    students_result = await db.execute(select(Student))
    students = students_result.scalars().all()
    
    sessions_result = await db.execute(
        select(ExamSession).where(ExamSession.is_active == True)
    )
    active_sessions = sessions_result.scalars().all()
    
    # Calculate averages
    all_sessions_result = await db.execute(select(ExamSession))
    all_sessions = all_sessions_result.scalars().all()
    
    avg_engagement = 0.0
    high_risk_count = 0
    
    if all_sessions:
        avg_engagement = sum(s.engagement_score for s in all_sessions) / len(all_sessions)
        high_risk_count = sum(1 for s in all_sessions if s.risk_score >= 60)
    
    return DashboardStats(
        total_students=len(students),
        active_sessions=len(active_sessions),
        average_engagement=round(avg_engagement, 2),
        high_risk_count=high_risk_count
    )
