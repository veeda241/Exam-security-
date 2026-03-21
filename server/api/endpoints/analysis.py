from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List
from datetime import datetime
import base64
import os
import cv2
import numpy as np
import uuid
import json

from supabase_client import get_supabase
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

router = APIRouter()
supabase = get_supabase()

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
    background_tasks: BackgroundTasks
):
    """Process webcam and screen data for AI analysis using Supabase"""
    
    try:
        # Access vision engine from app state
        vision_engine = getattr(request.app.state, "vision_engine", None)
        
        # 1. Verify session in Supabase
        session_res = supabase.table("exam_sessions").select("*").eq("id", analysis_request.session_id).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_res.data[0]
        
        # Prepare analysis record with all optional fields initialized to prevent Supabase schema errors
        analysis_data = {
            "id": str(uuid.uuid4()),
            "session_id": session["id"],
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_type": "MULTI_MODAL",
            "result_data": {},
            "risk_score_added": 0.0,
            "face_detected": True,
            "face_confidence": 1.0,
            "detected_text": "",
            "forbidden_keywords_found": [],
            "similarity_score": 0.0
        }
        
        # Track session updates
        session_updates = {}
        
        # 1. Webcam Analysis
        if analysis_request.webcam_image:
            webcam_frame = decode_image(analysis_request.webcam_image)
            if webcam_frame is not None:
                fname, fpath = save_image(webcam_frame, WEBCAM_DIR, "webcam")
                analysis_data["source_file"] = f"/uploads/webcam/{fname}"
                
                if vision_engine:
                    try:
                        vision_results = vision_engine.analyze_frame(webcam_frame)
                        violations = vision_results.get('violations', [])
                        is_face_detected = "FACE_NOT_FOUND" not in violations and "FACE_ABSENT_VIOLATION" not in violations
                        analysis_data["face_detected"] = is_face_detected
                        analysis_data["face_confidence"] = 0.0 if not is_face_detected else 0.9
                        
                        if "GAZE_AWAY_LONG" in violations:
                            session_updates["engagement_score"] = max(0, session.get("engagement_score", 100) - 5)
                        elif not is_face_detected:
                            session_updates["face_absence_count"] = session.get("face_absence_count", 0) + 1
                            session_updates["engagement_score"] = max(0, session.get("engagement_score", 100) - 10)
                        else:
                            session_updates["engagement_score"] = min(100, session.get("engagement_score", 100) + 1)

                        analysis_data["result_data"]["vision"] = vision_results
                        analysis_data["risk_score_added"] += vision_results.get('integrity_score_impact', 0)
                    except Exception as ve:
                        print(f"[Analysis] Vision Engine Error: {ve}")

                # Object Detection
                try:
                    from services.object_detection import get_object_detector
                    yolo = get_object_detector()
                    obj_result = yolo.detect(webcam_frame)
                    
                    if obj_result.get("forbidden_detected"):
                        analysis_data["result_data"]["objects"] = obj_result.get("objects", [])
                        analysis_data["risk_score_added"] += obj_result.get("risk_score", 0)
                except Exception as oe:
                    print(f"[Analysis] Object detection skip: {oe}")

        # 2. Screen Analysis (OCR)
        if analysis_request.screen_image:
            screen_frame = decode_image(analysis_request.screen_image)
            if screen_frame is not None:
                fname, fpath = save_image(screen_frame, SCREENSHOTS_DIR, "screen")
                ocr_result = await analyze_screenshot_ocr(fpath)
                
                analysis_data["detected_text"] = ocr_result.get("text", "")
                analysis_data["forbidden_keywords_found"] = ocr_result.get("forbidden_keywords", [])
                
                if ocr_result.get("forbidden_detected"):
                    session_updates["forbidden_site_count"] = session.get("forbidden_site_count", 0) + 1
                    session_updates["content_relevance"] = max(0, session.get("content_relevance", 100) - 20)
                    analysis_data["risk_score_added"] += ocr_result.get("risk_score", 0)
                
                analysis_data["result_data"]["ocr"] = ocr_result

        # 3. Text Similarity (Clipboard)
        if analysis_request.clipboard_text:
            try:
                sim_result = await check_text_similarity(analysis_request.clipboard_text)
                analysis_data["similarity_score"] = sim_result.get("similarity_score", 0)
                if sim_result.get("is_suspicious"):
                    session_updates["effort_alignment"] = max(0, session.get("effort_alignment", 100) - 15)
                    analysis_data["risk_score_added"] += sim_result.get("risk_score", 0)
                
                analysis_data["result_data"]["similarity"] = sim_result
            except Exception as se:
                print(f"[Analysis] Similarity Check Error: {se}")

        # 4. LLM Analysis (Optional)
        try:
            llm = get_llm_service()
            if await llm.check_connection():
                llm_result = await llm.analyze_behavior(
                    text=analysis_data.get("detected_text", ""),
                    violations=analysis_data.get("forbidden_keywords_found", [])
                )
                if llm_result.get("is_cheating"):
                    analysis_data["risk_score_added"] += 25
                    analysis_data["result_data"]["llm_analysis"] = llm_result
        except Exception as le:
            print(f"[Analysis] LLM Analysis Error: {le}")

        # Save Analysis Result to Supabase
        supabase.table("analysis_results").insert(analysis_data).execute()
        
        # Update Session Risk
        current_risk = session.get("risk_score", 0.0)
        new_risk = min(100, current_risk + analysis_data["risk_score_added"])
        session_updates["risk_score"] = new_risk
        
        if new_risk > 85:
            session_updates["risk_level"] = "suspicious"
        elif new_risk > 60:
            session_updates["risk_level"] = "review"
        else:
            session_updates["risk_level"] = "safe"
            
        if session_updates:
            supabase.table("exam_sessions").update(session_updates).eq("id", session["id"]).execute()
        
        return AnalysisResponse(
            status="processed",
            risk_score=new_risk,
            face_detected=analysis_data["face_detected"],
            forbidden_detected=len(analysis_data.get("forbidden_keywords_found", [])) > 0,
            similarity_score=analysis_data.get("similarity_score", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=List[StudentSummary])
async def get_dashboard_data():
    """Get summarized student data for dashboard using Supabase"""
    
    try:
        # Get all students
        students_res = supabase.table("students").select("*").execute()
        students = students_res.data
        
        dashboard_data = []
        
        for student in students:
            # Get latest session for this student
            session_res = supabase.table("exam_sessions")\
                .select("*")\
                .eq("student_id", student["id"])\
                .order("started_at", desc=True)\
                .limit(1).execute()
            
            session = session_res.data[0] if session_res.data else None
            
            if session:
                dashboard_data.append(StudentSummary(
                    id=student["id"],
                    name=student["name"],
                    email=student.get("email"),
                    department=student.get("department"),
                    year=student.get("year"),
                    latest_session_id=session["id"],
                    risk_score=session.get("risk_score", 0),
                    engagement_score=session.get("engagement_score", 0),
                    effort_alignment=session.get("effort_alignment", 0),
                    content_relevance=session.get("content_relevance", 0),
                    tab_switch_count=session.get("tab_switch_count", 0),
                    forbidden_site_count=session.get("forbidden_site_count", 0),
                    copy_count=session.get("copy_count", 0),
                    status=session.get("risk_level", "safe")
                ))
            else:
                dashboard_data.append(StudentSummary(
                    id=student["id"],
                    name=student["name"],
                    email=student.get("email"),
                    department=student.get("department"),
                    year=student.get("year"),
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}")
async def get_student_details(student_id: str):
    """Get detailed analysis for a specific student from Supabase"""
    
    try:
        student_res = supabase.table("students").select("*").eq("id", student_id).execute()
        if not student_res.data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = student_res.data[0]
        
        sessions_res = supabase.table("exam_sessions")\
            .select("*")\
            .eq("student_id", student_id)\
            .order("started_at", desc=True).execute()
        
        return {
            "student": student,
            "sessions": sessions_res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get overall dashboard statistics from Supabase"""
    
    try:
        # 1. Total Students
        students_res = supabase.table("students").select("id", count="exact").execute()
        total_students = students_res.count if hasattr(students_res, 'count') else len(students_res.data)
        
        # 2. Active Sessions
        active_res = supabase.table("exam_sessions").select("id", count="exact").eq("is_active", True).execute()
        active_sessions_count = active_res.count if hasattr(active_res, 'count') else len(active_res.data)
        
        # 3. Calculate averages from all sessions
        all_sessions_res = supabase.table("exam_sessions").select("risk_score", "engagement_score").execute()
        all_sessions = all_sessions_res.data
        
        avg_engagement = 0.0
        high_risk_count = 0
        
        if all_sessions:
            avg_engagement = sum(s.get("engagement_score", 0) for s in all_sessions) / len(all_sessions)
            high_risk_count = sum(1 for s in all_sessions if s.get("risk_score", 0) >= 60)
        
        return DashboardStats(
            total_students=total_students,
            active_sessions=active_sessions_count,
            average_engagement=round(avg_engagement, 2),
            high_risk_count=high_risk_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
