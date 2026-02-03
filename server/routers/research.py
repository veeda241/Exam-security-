from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from database import get_db
from models.research import ResearchJourney, SearchStrategy
from services.research_analysis import analyze_research_journey

router = APIRouter()

@router.get("/session/{session_id}/analysis")
async def get_research_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves and analyzes the student's research path"""
    
    # Get all journey steps
    result = await db.execute(
        select(ResearchJourney).where(ResearchJourney.session_id == session_id).order_by(ResearchJourney.timestamp.asc())
    )
    journey_steps = result.scalars().all()
    
    if not journey_steps:
        return {"success": False, "message": "No research data found"}

    # Prepare data for analysis engine
    journey_data = [
        {"url": step.url, "title": step.title, "dwell_time": step.dwell_time}
        for step in journey_steps
    ]
    
    analysis = analyze_research_journey(journey_data)
    
    # Optional: Save/Update SearchStrategy in DB
    # (Logic to persist analysis could go here)
    
    return {
        "success": True,
        "session_id": session_id,
        "journey": journey_data,
        "analysis": analysis
    }
