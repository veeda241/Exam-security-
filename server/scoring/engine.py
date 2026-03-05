"""
ExamGuard Pro - Scoring Engine
Calculates engagement, relevance, effort, and risk metrics.
Uses BROWSING_SUMMARY events from chrome.tabs-based tracker for
time-on-site and per-category browsing analysis.
"""

from typing import List, Dict, Any, Optional
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
    def _get_latest_browsing_summary(events) -> Optional[Dict]:
        """Extract the most recent BROWSING_SUMMARY event data from events."""
        summaries = [
            e for e in events 
            if e.event_type == "BROWSING_SUMMARY" and e.data
        ]
        if not summaries:
            return None
        # Sort by timestamp (most recent last) and return the latest
        summaries.sort(key=lambda e: e.client_timestamp or 0)
        return summaries[-1].data
    
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
        
        # ====== Extract Browsing Summary from chrome.tabs tracker ======
        browsing = ScoringEngine._get_latest_browsing_summary(events)
        # browsing keys: timeByCategory, totalTime, browsingRiskScore, effortScore,
        #   uniqueSitesVisited, flaggedSitesCount, openTabsCount, flaggedOpenTabs,
        #   topFlaggedSites, examTimePercent, distractionTimePercent
        
        time_by_cat = browsing.get("timeByCategory", {}) if browsing else {}
        total_browse_time = browsing.get("totalTime", 0) if browsing else 0
        exam_time_pct = browsing.get("examTimePercent", 0) if browsing else 0
        distraction_time_pct = browsing.get("distractionTimePercent", 0) if browsing else 0
        ext_browsing_risk = browsing.get("browsingRiskScore", 0) if browsing else 0
        ext_effort_score = browsing.get("effortScore", 100) if browsing else 100
        flagged_sites_count = browsing.get("flaggedSitesCount", 0) if browsing else 0
        flagged_open_tabs = browsing.get("flaggedOpenTabs", 0) if browsing else 0
        
        # 1. Calculate Engagement Score (0-100)
        # Base: 100
        # Penalties: Face absence, Tab switching, Window blur, Site distractions
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
        
        # Distraction time penalty (from browsing tracker)
        if distraction_time_pct > 10:
            engagement -= min((distraction_time_pct - 10) * 0.8, 25)  # Up to 25 pts
        
        # Flagged open tabs penalty
        engagement -= min(flagged_open_tabs * 3, 15)
        
        session.engagement_score = max(engagement, 0)
        
        # 2. Calculate Content Relevance (0-100)
        # Based on OCR, Forbidden Keyword detection, and browsing patterns
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
        
        # Browsing-based relevance: penalize for low exam-time percentage
        if total_browse_time > 30000:  # Only if meaningful browsing time (>30s)
            if exam_time_pct < 50:
                relevance -= min((50 - exam_time_pct) * 0.6, 30)  # Up to 30 pts
                
        session.content_relevance = max(relevance, 0)
        
        # 3. Calculate Effort Alignment (0-100)
        # Effort is driven by how much time is spent on exam vs everything else.
        # If student is on exam platform => high effort. On movies/games => low effort.
        
        total_events = len(events)
        duration_seconds = 60.0 # Fallback
        if session.started_at:
            end = session.ended_at or datetime.utcnow()
            duration_seconds = max((end - session.started_at).total_seconds(), 1.0)
            
        duration_minutes = duration_seconds / 60.0
        events_per_minute = total_events / duration_minutes
        
        # ========== TIME-BASED Effort (chrome.tabs data) ==========
        ai_time_ms = time_by_cat.get("ai", 0)
        cheating_time_ms = time_by_cat.get("cheating", 0)
        entertainment_time_ms = time_by_cat.get("entertainment", 0)
        exam_time_ms = time_by_cat.get("exam", 0)
        other_time_ms = time_by_cat.get("other", 0)
        
        total_browse_ms = ai_time_ms + cheating_time_ms + entertainment_time_ms + exam_time_ms + other_time_ms
        
        if total_browse_ms > 5000:
            # Primary effort: based on exam time ratio
            exam_ratio = exam_time_ms / max(total_browse_ms, 1)
            effort = exam_ratio * 100
            
            # "Other" sites get minimal credit (10%)
            other_ratio = other_time_ms / max(total_browse_ms, 1)
            effort += other_ratio * 10
            
            # Bonus for >80% exam time
            if exam_ratio > 0.8:
                effort += 10
        else:
            # Not enough browsing data, use event-based heuristics
            effort = 60.0  # Neutral base when no browsing data
            
            # Activity-based adjustment
            if events_per_minute > 2 and events_per_minute < 15:
                effort += 15
            elif events_per_minute >= 15:
                effort -= 10
        
        # Copy/Paste impact
        if session.copy_count > 5:
            effort -= (session.copy_count - 5) * 5
        
        # Convert to seconds for count-based penalties
        ai_time_s = ai_time_ms / 1000
        cheating_time_s = cheating_time_ms / 1000
        entertainment_time_s = entertainment_time_ms / 1000
        
        # ========== Count-based Forbidden Site Impact (event-level) ==========
        ai_events = sum(1 for e in events if e.event_type == "FORBIDDEN_SITE" 
                       and e.data and e.data.get("category") == "AI")
        entertainment_events = sum(1 for e in events if e.event_type == "FORBIDDEN_SITE"
                                  and e.data and e.data.get("category") == "ENTERTAINMENT")
        cheating_events = sum(1 for e in events if e.event_type == "FORBIDDEN_SITE"
                             and e.data and e.data.get("category") == "CHEATING")
        
        # Additional per-visit penalties
        effort -= min(ai_events * 5, 25)
        effort -= min(entertainment_events * 3, 15)
        effort -= min(cheating_events * 8, 30)
        
        # General forbidden: fallback penalty
        general_forbidden = session.forbidden_site_count - (ai_events + entertainment_events + cheating_events)
        if general_forbidden > 0:
            effort -= min(general_forbidden * 5, 25)
        
        # Blend with extension's own effort score (30% weight)
        effort = effort * 0.7 + ext_effort_score * 0.3
            
        session.effort_alignment = max(min(effort, 100), 0)
        
        # 4. Behavioral Anomaly Detection Integration
        detector = get_detector()
        event_list = [e.to_dict() for e in events]
        anomaly_results = detector.analyze_session_behavior(event_list, duration_seconds)
        
        # ========== RISK SCORE (0-100) ==========
        # 30% Vision + 20% OCR/Similarity + 20% Anomaly + 30% Browsing
        vision_impact = sum([a.risk_score_added for a in analyses if a.analysis_type == "LIVE_VISION_ALERT"])
        ocr_impact = 100 - session.content_relevance
        anomaly_impact = anomaly_results.get("risk_score", 0)
        
        # Browsing-based risk (from chrome.tabs tracker)
        # Blend: extension's real-time score + server's time-based calculation
        time_based_browse_risk = 0
        if total_browse_time > 0:
            # Percentage of time on forbidden sites → risk
            time_based_browse_risk = min(distraction_time_pct * 1.5, 100)
        
        # Average of extension score and server calculation
        browsing_risk = (ext_browsing_risk + time_based_browse_risk) / 2
        
        # Tab audit: extra risk for many flagged open tabs
        tab_audit_events = [e for e in events if e.event_type == "TAB_AUDIT" and e.data]
        if tab_audit_events:
            latest_audit = max(tab_audit_events, key=lambda e: e.client_timestamp or 0)
            audit_flagged = latest_audit.data.get("flaggedTabs", 0)
            browsing_risk += min(audit_flagged * 5, 20)
        
        browsing_risk = min(browsing_risk, 100)
        
        # Direct forbidden site impact (bonus from categorized visits)
        forbidden_site_bonus = min((ai_events * 5) + (cheating_events * 8) + (entertainment_events * 3), 25)
        
        # Aggregate Risk Score
        agg_risk = (
            (vision_impact * 0.30) + 
            (ocr_impact * 0.20) + 
            (anomaly_impact * 0.20) + 
            (browsing_risk * 0.30) + 
            forbidden_site_bonus
        )
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
