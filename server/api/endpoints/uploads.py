from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
import base64
import os
import uuid

from supabase_client import get_supabase
from api.schemas import ImageUpload, UploadResponse
from config import SCREENSHOTS_DIR, WEBCAM_DIR

router = APIRouter()
supabase = get_supabase()

async def analyze_screenshot(
    session_id: str,
    file_id: str,
    file_path: str
):
    """Background task to analyze screenshot with OCR via Supabase"""
    from services.ocr import analyze_screenshot_ocr
    
    try:
        ocr_result = await analyze_screenshot_ocr(file_path)
        
        # Create analysis record in Supabase
        analysis_data = {
            "session_id": session_id,
            "analysis_type": "OCR",
            "detected_text": ocr_result.get("text", ""),
            "forbidden_keywords_found": ocr_result.get("forbidden_keywords", []),
            "risk_score_added": ocr_result.get("risk_score", 0),
            "result_data": ocr_result,
            "source_file": file_path,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        supabase.table("analysis_results").insert(analysis_data).execute()
        
        # Update session if forbidden content found
        if ocr_result.get("forbidden_detected"):
            session_res = supabase.table("exam_sessions").select("forbidden_site_count, risk_score").eq("id", session_id).execute()
            if session_res.data:
                s = session_res.data[0]
                supabase.table("exam_sessions").update({
                    "forbidden_site_count": s.get("forbidden_site_count", 0) + 1,
                    "risk_score": min(100, s.get("risk_score", 0) + ocr_result.get("risk_score", 0))
                }).eq("id", session_id).execute()
        
    except Exception as e:
        print(f"OCR Analysis error: {e}")


async def analyze_webcam_frame(
    session_id: str,
    file_id: str,
    file_path: str
):
    """Background task to analyze webcam frame for face detection via Supabase"""
    from services.face_detection import detect_face
    
    try:
        face_result = await detect_face(file_path)
        
        # Create analysis record in Supabase
        analysis_data = {
            "session_id": session_id,
            "analysis_type": "FACE",
            "face_detected": face_result.get("face_detected", False),
            "face_confidence": face_result.get("confidence", 0.0),
            "risk_score_added": face_result.get("risk_score", 0),
            "result_data": face_result,
            "source_file": file_path,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        supabase.table("analysis_results").insert(analysis_data).execute()
        
        # Update session if face not detected
        if not face_result.get("face_detected"):
            session_res = supabase.table("exam_sessions").select("face_absence_count, engagement_score").eq("id", session_id).execute()
            if session_res.data:
                s = session_res.data[0]
                supabase.table("exam_sessions").update({
                    "face_absence_count": s.get("face_absence_count", 0) + 1,
                    "engagement_score": max(0, s.get("engagement_score", 100) - 5)
                }).eq("id", session_id).execute()
        
    except Exception as e:
        print(f"Face Detection error: {e}")


@router.post("/screenshot", response_model=UploadResponse)
async def upload_screenshot(
    upload: ImageUpload,
    background_tasks: BackgroundTasks
):
    """Upload a screenshot for analysis using Supabase context"""
    
    # Generate file ID and path
    file_id = f"ss_{upload.session_id}_{upload.timestamp}_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(SCREENSHOTS_DIR, f"{file_id}.jpg")
    
    try:
        # Decode and save image
        image_data = upload.image_data
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        image_bytes = base64.b64decode(image_data)
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
    
    # Trigger OCR analysis in background
    background_tasks.add_task(
        analyze_screenshot,
        upload.session_id,
        file_id,
        file_path
    )
    
    return UploadResponse(
        success=True,
        file_id=file_id,
        analysis_triggered=True,
    )


@router.post("/webcam", response_model=UploadResponse)
async def upload_webcam_frame(
    upload: ImageUpload,
    background_tasks: BackgroundTasks
):
    """Upload a webcam frame for face detection using Supabase context"""
    
    # Generate file ID and path
    file_id = f"wc_{upload.session_id}_{upload.timestamp}_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(WEBCAM_DIR, f"{file_id}.jpg")
    
    try:
        # Decode and save image
        image_data = upload.image_data
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        image_bytes = base64.b64decode(image_data)
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
    
    # Trigger face detection in background
    background_tasks.add_task(
        analyze_webcam_frame,
        upload.session_id,
        file_id,
        file_path
    )
    
    return UploadResponse(
        success=True,
        file_id=file_id,
        analysis_triggered=True,
    )


@router.delete("/cleanup/{session_id}")
async def cleanup_session_uploads(session_id: str):
    """Delete all uploaded files for a session"""
    
    deleted_count = 0
    errors = []
    
    # Clean screenshots
    if os.path.exists(SCREENSHOTS_DIR):
        for filename in os.listdir(SCREENSHOTS_DIR):
            if session_id in filename:
                try:
                    os.remove(os.path.join(SCREENSHOTS_DIR, filename))
                    deleted_count += 1
                except Exception as e:
                    errors.append(str(e))
    
    # Clean webcam frames
    if os.path.exists(WEBCAM_DIR):
        for filename in os.listdir(WEBCAM_DIR):
            if session_id in filename:
                try:
                    os.remove(os.path.join(WEBCAM_DIR, filename))
                    deleted_count += 1
                except Exception as e:
                    errors.append(str(e))
    
    return {
        "success": len(errors) == 0,
        "deleted_count": deleted_count,
        "errors": errors
    }
