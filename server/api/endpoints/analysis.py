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
from services.research_analysis import analyze_research_journey

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
        from typing import Dict, Any
        analysis_data: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "session_id": session["id"],
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_type": "MULTI_MODAL",
            "result_data": {
                "multiface_detected": False,
                "phone_detected": False
            },
            "risk_score_added": 0.0,
            "face_detected": True,
            "face_confidence": 1.0,
            "detected_text": "",
            "forbidden_keywords_found": [],
            "similarity_score": 0.0
        }
        
        # Track session updates
        session_updates: Dict[str, Any] = {}
        
        # 1. Webcam Analysis
        if analysis_request.webcam_image:
            webcam_frame = decode_image(analysis_request.webcam_image)
            if webcam_frame is not None:
                fname, fpath = save_image(webcam_frame, WEBCAM_DIR, "webcam")
                analysis_data["source_file"] = f"/uploads/webcam/{fname}"
                session_updates["latest_webcam"] = f"/uploads/webcam/{fname}"
                
                if vision_engine:
                    try:
                        vision_results = vision_engine.analyze_frame(webcam_frame)
                        violations = vision_results.get('violations', [])
                        is_face_detected = "FACE_NOT_FOUND" not in violations and "FACE_ABSENT_VIOLATION" not in violations
                        is_multiface = "MULTIPLE_FACES_DETECTED" in violations
                        
                        analysis_data["face_detected"] = is_face_detected
                        analysis_data["result_data"]["multiface_detected"] = is_multiface
                        analysis_data["face_confidence"] = 0.0 if not is_face_detected else 0.9
                        
                        if "GAZE_AWAY_LONG" in violations:
                            session_updates["engagement_score"] = max(0, (session.get("engagement_score") or 100) - 5)
                        elif not is_face_detected:
                            session_updates["face_absence_count"] = (session.get("face_absence_count") or 0) + 1
                            session_updates["engagement_score"] = max(0, (session.get("engagement_score") or 100) - 10)
                        elif is_multiface:
                            session_updates["multiface_count"] = (session.get("multiface_count") or 0) + 1
                            session_updates["engagement_score"] = max(0, (session.get("engagement_score") or 100) - 15)
                        else:
                            session_updates["engagement_score"] = min(100, (session.get("engagement_score") or 100) + 1)

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
                        objects = obj_result.get("objects", [])
                        analysis_data["result_data"]["objects"] = objects
                        analysis_data["risk_score_added"] += obj_result.get("risk_score", 0)
                        
                        # Check for phone specifically
                        has_phone = any(o.get('object', '') == 'cell phone' for o in objects)
                        analysis_data["result_data"]["phone_detected"] = has_phone
                        
                        if has_phone:
                            session_updates["phone_detection_count"] = (session.get("phone_detection_count") or 0) + 1
                            print(f"[Analysis] phone_detected for session: {session.get('id')}")
                except Exception as oe:
                    print(f"[Analysis] Object detection skip: {oe}")

        # 2. Screen Analysis (OCR)
        if analysis_request.screen_image:
            screen_frame = decode_image(analysis_request.screen_image)
            if screen_frame is not None:
                fname, fpath = save_image(screen_frame, SCREENSHOTS_DIR, "screen")
                session_updates["latest_screenshot"] = f"/uploads/screenshots/{fname}"
                ocr_result = await analyze_screenshot_ocr(fpath)
                
                analysis_data["detected_text"] = ocr_result.get("text", "")
                analysis_data["forbidden_keywords_found"] = ocr_result.get("forbidden_keywords", [])
                
                if ocr_result.get("forbidden_detected"):
                    session_updates["forbidden_site_count"] = (session.get("forbidden_site_count") or 0) + 1
                    session_updates["content_relevance"] = max(0, (session.get("content_relevance") or 100) - 20)
                    analysis_data["risk_score_added"] += ocr_result.get("risk_score", 0)
                
                analysis_data["result_data"]["ocr"] = ocr_result

        # 3. Text Similarity (Clipboard)
        if analysis_request.clipboard_text:
            try:
                sim_result = await check_text_similarity(analysis_request.clipboard_text)
                analysis_data["similarity_score"] = sim_result.get("similarity_score", 0)
                if sim_result.get("is_suspicious"):
                    session_updates["effort_alignment"] = max(0, (session.get("effort_alignment") or 100) - 15)
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
                    analysis_data["risk_score_added"] = float(analysis_data["risk_score_added"]) + 25
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
        
        # Safely determine if forbidden keywords were found
        forbidden_keywords = analysis_data.get("forbidden_keywords_found")
        has_forbidden = len(forbidden_keywords) > 0 if isinstance(forbidden_keywords, list) else False
        
        return AnalysisResponse(
            status="processed",
            risk_score=new_risk,
            face_detected=analysis_data.get("face_detected", True),
            multiface_detected=analysis_data.get("result_data", {}).get("multiface_detected", False),
            phone_detected=analysis_data.get("result_data", {}).get("phone_detected", False),
            looking_away="GAZE_AWAY_LONG" in (analysis_data.get("result_data", {}).get("vision", {}).get("violations", []) or []),
            speaking_detected="SPEAKING_DETECTED" in (analysis_data.get("result_data", {}).get("vision", {}).get("violations", []) or []),
            is_suspicious_gaze="SUSPICIOUS_GAZE_PATTERN" in (analysis_data.get("result_data", {}).get("vision", {}).get("violations", []) or []),
            forbidden_detected=has_forbidden,
            similarity_score=analysis_data.get("similarity_score", 0.0)
        )
    except Exception as e:
        import traceback
        print(f"[ERROR] Detailed Analysis Crash: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/dashboard", response_model=List[StudentSummary])
async def get_dashboard_data():
    """Aggregates real-time student activity for the dashboard using bulk queries (Optimized)"""
    
    try:
        # 1. Fetch all students
        students_res = supabase.table("students").select("*").execute()
        students = students_res.data or []
        
        # 2. Fetch ALL sessions for these students (ordered by started_at to find latest)
        sessions_res = supabase.table("exam_sessions").select("*").order("started_at", desc=True).execute()
        sessions = sessions_res.data or []
        
        # 3. Create a mapping of student_id -> latest_session
        latest_sessions = {}
        for s in sessions:
            if s["student_id"] not in latest_sessions:
                latest_sessions[s["student_id"]] = s
        
        # 4. Fetch the latest research entry for EACH active session in bulk
        # Since we can't easily do a "latest by group" in a single simple Supabase query without RPC,
        # we'll fetch recently active research entries and map them.
        # Alternatively, for simplicity/safety, we'll keep the single-fetch logic but wrapped in safety.
        
        dashboard_data = []
        for student in students:
            session = latest_sessions.get(student["id"])
            
            summary_dict = {
                "id": str(student.get("id", "")),
                "name": str(student.get("name", "Unknown")),
                "email": student.get("email"),
                "department": student.get("department"),
                "year": student.get("year"),
                "status": "inactive",
                "risk_score": 0.0,
                "engagement_score": 0.0,
                "effort_alignment": 0.0,
                "content_relevance": 0.0,
                "tab_switch_count": 0,
                "forbidden_site_count": 0,
                "copy_count": 0,
                "latest_session_id": None,
                "last_visited_url": None,
                "last_visited_title": None,
                "effort_score": 0.0,
                "browsing_risk_score": 0.0,
                "phone_detection_count": 0
            }
            
            if session:
                summary_dict.update({
                    "latest_session_id": session.get("id"),
                    "status": session.get("risk_level") or session.get("status") or "safe",
                    "risk_score": float(session.get("risk_score") or 0.0),
                    "engagement_score": float(session.get("engagement_score") or 0.0),
                    "effort_alignment": float(session.get("effort_alignment") or 0.0),
                    "content_relevance": float(session.get("content_relevance") or 0.0),
                    "tab_switch_count": int(session.get("tab_switch_count") or 0),
                    "forbidden_site_count": int(session.get("forbidden_site_count") or 0),
                    "copy_count": int(session.get("copy_count") or 0),
                    "face_absence_count": int(session.get("face_absence_count") or 0),
                    "multiface_count": int(session.get("multiface_count") or 0),
                    "phone_detection_count": int(session.get("phone_detection_count") or 0),
                    "latest_screenshot": session.get("latest_screenshot"),
                    "latest_webcam": session.get("latest_webcam"),
                    "last_active": session.get("updated_at")
                })
                
                # Fetch recent journey for this session to get dynamic effort/risk scores
                try:
                    journey_res = supabase.table("research_journey")\
                        .select("url,title")\
                        .eq("session_id", session["id"])\
                        .order("timestamp", desc=True)\
                        .limit(20)\
                        .execute()
                    
                    if journey_res.data:
                        # Journey exists, run analysis
                        analysis = analyze_research_journey(journey_res.data)
                        summary_dict["effort_score"] = analysis.get("effort_score", 0.0)
                        summary_dict["browsing_risk_score"] = analysis.get("browsing_risk_score", 0.0)
                        # Map browsing_risk to status if risk is high
                        if summary_dict["browsing_risk_score"] > 60.0:
                            summary_dict["status"] = "review"
                except Exception as b_err:
                    print(f"[Dashboard] Browsing analysis failed for {session['id']}: {b_err}")
                
                # Check if online (active in last 2 minutes)
                updated_str = session.get("updated_at") or session.get("created_at")
                if updated_str:
                    try:
                        from datetime import timezone
                        updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                        diff = datetime.now(timezone.utc) - updated_dt
                        if diff.total_seconds() < 120:
                            summary_dict["is_online"] = True
                    except:
                        pass
                
                # Try to get active site info
                try:
                    site_res = supabase.table("research_journey")\
                        .select("url", "title")\
                        .eq("session_id", session["id"])\
                        .order("timestamp", desc=True)\
                        .limit(1).execute()
                    
                    if site_res.data:
                        summary_dict["last_visited_url"] = site_res.data[0].get("url")
                        summary_dict["last_visited_title"] = site_res.data[0].get("title")
                except:
                    pass
            
            dashboard_data.append(StudentSummary(**summary_dict))
            
        return dashboard_data
    except Exception as e:
        print(f"[FATAL] Dashboard aggregate failed: {str(e)}")
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
