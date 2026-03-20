from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from typing import List
import os

from supabase_client import get_supabase
from api.schemas import ReportRequest, ReportSummary
from reports.generator import generate_pdf_report

router = APIRouter()
supabase = get_supabase()


@router.get("/session/{session_id}/summary", response_model=ReportSummary)
async def get_report_summary(session_id: str):
    """Get a summary report for a session from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = res.data[0]
        
        # Get high risk events
        events_res = supabase.table("events").select("*").eq("session_id", session_id).gte("risk_weight", 15).order("timestamp", desc=True).limit(20).execute()
        high_risk_events = events_res.data
        
        # Calculate duration
        start_time = datetime.fromisoformat(session["started_at"].replace('Z', '+00:00')) if session.get("started_at") else datetime.utcnow()
        end_time_str = session.get("ended_at")
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')) if end_time_str else datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return ReportSummary(
            session_id=session_id,
            student_name=session.get("student_name", "Unknown"),
            exam_id=session.get("exam_id", "Unknown"),
            duration_seconds=duration,
            risk_score=session.get("risk_score", 0.0),
            risk_level=session.get("risk_level", "low"),
            event_counts={
                "tab_switches": session.get("tab_switch_count", 0),
                "copy_events": session.get("copy_count", 0),
                "face_absences": session.get("face_absence_count", 0),
                "forbidden_sites": session.get("forbidden_site_count", 0),
                "total": session.get("total_events", 0),
            },
            high_risk_events=high_risk_events,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/json")
async def get_json_report(session_id: str):
    """Get full JSON report for a session from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = res.data[0]
        
        # Get all events
        events_res = supabase.table("events").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        events = events_res.data
        
        # Get analysis results
        analysis_res = supabase.table("analysis_results").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        analyses = analysis_res.data
        
        # Calculate duration
        start_time = datetime.fromisoformat(session["started_at"].replace('Z', '+00:00')) if session.get("started_at") else datetime.utcnow()
        end_time_str = session.get("ended_at")
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')) if end_time_str else datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "report": {
                "generated_at": datetime.utcnow().isoformat(),
                "session": session,
                "duration_seconds": duration,
                "events": events,
                "analysis_results": analyses,
                "risk_breakdown": {
                    "score": session.get("risk_score", 0.0),
                    "level": session.get("risk_level", "low"),
                    "thresholds": {
                        "safe": "0-30",
                        "review": "30-60",
                        "suspicious": "60+",
                    },
                },
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/pdf")
async def get_pdf_report_route(session_id: str):
    """Generate and download PDF report for a session from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = res.data[0]
        
        # Get events
        events_res = supabase.table("events").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        events = events_res.data
        
        # Generate PDF
        pdf_path = await generate_pdf_report(session, events)
        
        return FileResponse(
            path=pdf_path,
            filename=f"report_{session_id}.pdf",
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/session/{session_id}/timeline")
async def get_session_timeline(session_id: str):
    """Get event timeline for visualization from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = res.data[0]
        
        # Get all events
        events_res = supabase.table("events").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        events = events_res.data
        
        # Build timeline with risk progression
        timeline = []
        cumulative_risk = 0
        
        for event in events:
            weight = event.get("risk_weight", 0)
            cumulative_risk += weight
            timeline.append({
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "risk_weight": weight,
                "cumulative_risk": cumulative_risk,
                "data": event.get("data")
            })
        
        return {
            "session_id": session_id,
            "start_time": session.get("started_at"),
            "end_time": session.get("ended_at"),
            "final_risk": session.get("risk_score", 0.0),
            "timeline": timeline
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
