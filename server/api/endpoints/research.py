from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from supabase_client import get_supabase
from services.research_analysis import analyze_research_journey

router = APIRouter()
supabase = get_supabase()


@router.get("/session/{session_id}/analysis")
async def get_research_analysis(session_id: str):
    """Retrieves and analyzes the student's research path from Supabase"""
    
    try:
        # Get all journey steps
        res = supabase.table("research_journey").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        journey_steps = res.data
        
        if not journey_steps:
            return {"success": False, "message": "No research data found"}

        # Prepare data for analysis engine
        journey_data = [
            {"url": step.get("url"), "title": step.get("title"), "dwell_time": step.get("dwell_time", 0)}
            for step in journey_steps
        ]
        
        analysis = analyze_research_journey(journey_data)
        
        return {
            "success": True,
            "session_id": session_id,
            "journey": journey_data,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/journey")
async def get_research_journey(session_id: str):
    """Get raw research journey data for a session from Supabase"""
    try:
        res = supabase.table("research_journey").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        journey_steps = res.data
        
        return {
            "session_id": session_id,
            "total_steps": len(journey_steps),
            "journey": journey_steps
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/strategy")
async def get_search_strategy(session_id: str):
    """Get search strategy analysis for a session from Supabase"""
    try:
        res = supabase.table("search_strategy").select("*").eq("session_id", session_id).order("analyzed_at", desc=True).limit(1).execute()
        strategy = res.data[0] if res.data else None
        
        if not strategy:
            return {
                "success": False,
                "message": "No strategy analysis found. Run analysis first."
            }
        
        return {
            "success": True,
            "session_id": session_id,
            "strategy": strategy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/analyze")
async def trigger_research_analysis(session_id: str):
    """Trigger fresh analysis of research journey via Supabase"""
    
    try:
        # Get journey data
        res = supabase.table("research_journey").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        journey_steps = res.data
        
        if not journey_steps:
            raise HTTPException(status_code=404, detail="No research data found")
        
        # Prepare and analyze
        journey_data = [
            {"url": step.get("url"), "title": step.get("title"), "dwell_time": step.get("dwell_time", 0)}
            for step in journey_steps
        ]
        
        analysis = analyze_research_journey(journey_data)
        
        # Save strategy
        strategy = {
            "session_id": session_id,
            "search_count": analysis.get("search_count", 0),
            "unique_sources": analysis.get("unique_sources", 0),
            "avg_dwell_time": analysis.get("avg_dwell_time", 0.0),
            "depth_score": analysis.get("depth_score", 0.0),
            "breadth_score": analysis.get("breadth_score", 0.0),
            "strategy_type": analysis.get("strategy_type", "unknown"),
            "effort_indicator": analysis.get("effort_indicator", 0.0),
            "analysis_data": analysis,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("search_strategy").insert(strategy).execute()
        
        return {
            "success": True,
            "session_id": session_id,
            "analysis": analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
