"""
ExamGuard Pro - Research Endpoint
API routes for research journey analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

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
        select(ResearchJourney)
        .where(ResearchJourney.session_id == session_id)
        .order_by(ResearchJourney.timestamp.asc())
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
    
    return {
        "success": True,
        "session_id": session_id,
        "journey": journey_data,
        "analysis": analysis
    }


@router.get("/session/{session_id}/journey")
async def get_research_journey(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get raw research journey data for a session"""
    
    result = await db.execute(
        select(ResearchJourney)
        .where(ResearchJourney.session_id == session_id)
        .order_by(ResearchJourney.timestamp.asc())
    )
    journey_steps = result.scalars().all()
    
    return {
        "session_id": session_id,
        "total_steps": len(journey_steps),
        "journey": [step.to_dict() for step in journey_steps]
    }


@router.get("/session/{session_id}/strategy")
async def get_search_strategy(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get search strategy analysis for a session"""
    
    result = await db.execute(
        select(SearchStrategy)
        .where(SearchStrategy.session_id == session_id)
        .order_by(SearchStrategy.analyzed_at.desc())
        .limit(1)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        return {
            "success": False,
            "message": "No strategy analysis found. Run analysis first."
        }
    
    return {
        "success": True,
        "session_id": session_id,
        "strategy": strategy.to_dict()
    }


@router.post("/session/{session_id}/analyze")
async def trigger_research_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Trigger fresh analysis of research journey"""
    
    # Get journey data
    result = await db.execute(
        select(ResearchJourney)
        .where(ResearchJourney.session_id == session_id)
        .order_by(ResearchJourney.timestamp.asc())
    )
    journey_steps = result.scalars().all()
    
    if not journey_steps:
        raise HTTPException(status_code=404, detail="No research data found")
    
    # Prepare and analyze
    journey_data = [
        {"url": step.url, "title": step.title, "dwell_time": step.dwell_time}
        for step in journey_steps
    ]
    
    analysis = analyze_research_journey(journey_data)
    
    # Save strategy
    strategy = SearchStrategy(
        session_id=session_id,
        search_count=analysis.get("search_count", 0),
        unique_sources=analysis.get("unique_sources", 0),
        avg_dwell_time=analysis.get("avg_dwell_time", 0.0),
        depth_score=analysis.get("depth_score", 0.0),
        breadth_score=analysis.get("breadth_score", 0.0),
        strategy_type=analysis.get("strategy_type", "unknown"),
        effort_indicator=analysis.get("effort_indicator", 0.0),
        analysis_data=analysis
    )
    
    db.add(strategy)
    await db.commit()
    
    return {
        "success": True,
        "session_id": session_id,
        "analysis": analysis
    }
