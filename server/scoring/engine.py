"""
ExamGuard Pro - Scoring Engine
Calculates engagement, relevance, effort, and risk metrics
"""

from typing import List, Dict, Any
from datetime import datetime
from models.session import ExamSession
from models.event import Event
from models.analysis import AnalysisResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from services.anomaly import get_detector
from services.similarity import get_checker

class ScoringEngine:
    """Advanced scoring for student analysis"""
    
    @staticmethod
    async def update_session_scores(session_id: str, db: AsyncSession):
        """Calculate and update all scores for a session"""
        
        # Get session
        result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return
            
        # Get events
        events_result = await db.execute(select(Event).where(Event.session_id == session_id))
        events = events_result.scalars().all()
        
        # Get analysis results
        analysis_result = await db.execute(select(AnalysisResult).where(AnalysisResult.session_id == session_id))
        analyses = analysis_result.scalars().all()
        
        # 1. Calculate Engagement Score (0-100)
        # Base: 100
        # Penalties: Face absence, Tab switching, Window blur
        engagement = 100.0
        
        face_detections = [a for a in analyses if a.analysis_type == "FACE_DETECTION"]
        if face_detections:
            absent_count = sum(1 for a in face_detections if not a.face_detected)
            absence_ratio = absent_count / len(face_detections)
            engagement -= (absence_ratio * 40) # Up to 40 points penalty
            
        # Tab switch penalty (sliding scale)
        tab_switches = session.tab_switch_count
        engagement -= min(tab_switches * 2, 30) # Up to 30 points penalty
        
        # Window blur penalty
        blurs = sum(1 for e in events if e.event_type == "WINDOW_BLUR")
        engagement -= min(blurs * 5, 20) # Up to 20 points penalty
        
        session.engagement_score = max(engagement, 0)
        
        # 2. Calculate Content Relevance (0-100)
        # Based on OCR and Forbidden Keyword detection
        relevance = 100.0
        forbidden_hits = session.forbidden_site_count
        relevance -= min(forbidden_hits * 25, 100)
        
        ocr_results = [a for a in analyses if a.analysis_type == "OCR"]
        checker = get_checker()
        for ocr in ocr_results:
            if ocr.result_data and ocr.result_data.get("forbidden_detected"):
                relevance -= 10
            
            # Check for similarities if text is available
            if ocr.detected_text:
                sim_result = checker.check_similarity(ocr.detected_text)
                if sim_result.get("is_suspicious"):
                    relevance -= sim_result.get("risk_score", 10)
                
        session.content_relevance = max(relevance, 0)
        
        # 3. Calculate Effort Alignment (0-100)
        # Based on event density and patterns
        effort = 80.0 # Start with a healthy base
        
        total_events = len(events)
        duration_seconds = 60.0 # Fallback
        if session.started_at:
            end = session.ended_at or datetime.utcnow()
            duration_seconds = max((end - session.started_at).total_seconds(), 1.0)
            
        duration_minutes = duration_seconds / 60.0
        events_per_minute = total_events / duration_minutes
        
        # High activity is good, too high/too low might be suspicious
        if events_per_minute > 2 and events_per_minute < 15:
            effort += 20
        elif events_per_minute >= 15:
            effort -= 10 # Rapid bursts often mean copy-paste
            
        # Copy/Paste impact
        if session.copy_count > 5:
            effort -= (session.copy_count - 5) * 5
            
        session.effort_alignment = max(min(effort, 100), 0)
        
        # 4. Behavioral Anomaly Detection Integration
        detector = get_detector()
        event_list = [e.to_dict() for e in events]
        anomaly_results = detector.analyze_session_behavior(event_list, duration_seconds)
        
        # Update session risk score based on all factors
        # 40% from visions violations + 30% OCR/Sim + 30% Anomalies
        vision_impact = sum([a.risk_score_added for a in analyses if a.analysis_type == "LIVE_VISION_ALERT"])
        ocr_impact = 100 - session.content_relevance
        anomaly_impact = anomaly_results.get("risk_score", 0)
        
        # Aggregate Risk Score (0-100)
        agg_risk = (vision_impact * 0.4) + (ocr_impact * 0.3) + (anomaly_impact * 0.3)
        session.risk_score = min(max(agg_risk, 0), 100)
        
        # 5. Update Risk Level
        if session.risk_score < 30:
            session.risk_level = "safe"
        elif session.risk_score < 60:
            session.risk_level = "review"
        else:
            session.risk_level = "suspicious"
            
        # Final Status Update
        if session.risk_score > 70:
            session.status = "flagged"
            
        await db.commit()
