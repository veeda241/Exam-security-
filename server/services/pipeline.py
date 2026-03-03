"""
ExamGuard Pro - Real-Time Analysis Pipeline
Connects extension events → transformer analysis → database updates → WebSocket push

Runs as a background task that processes incoming events through the AI pipeline
and pushes results to the dashboard in real time.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database import async_session
from models.session import ExamSession
from models.event import Event
from models.analysis import AnalysisResult


class AnalysisPipeline:
    """
    Real-time analysis pipeline that:
    1. Receives events from the extension
    2. Runs transformer + similarity analysis
    3. Updates the database with results
    4. Pushes updates to dashboard via WebSocket
    """

    def __init__(self):
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._stats = {
            "events_processed": 0,
            "transformer_analyses": 0,
            "db_updates": 0,
            "errors": 0,
        }

    async def start(self):
        """Start the pipeline background worker."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker())
        print("[Pipeline] Real-time analysis pipeline started")

    async def stop(self):
        """Stop the pipeline."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[Pipeline] Analysis pipeline stopped")

    async def submit(self, event_data: Dict[str, Any]):
        """Submit an event for pipeline processing."""
        await self._queue.put(event_data)

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": self._running,
        }

    async def _worker(self):
        """Background worker that processes events from the queue."""
        while self._running:
            try:
                # Wait for event with timeout (allows clean shutdown)
                try:
                    event_data = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                await self._process_event(event_data)
                self._stats["events_processed"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["errors"] += 1
                print(f"[Pipeline] Error processing event: {e}")
                await asyncio.sleep(0.5)

    async def _process_event(self, event_data: Dict[str, Any]):
        """Process a single event through the analysis pipeline."""
        event_type = event_data.get("type", "")
        session_id = event_data.get("session_id", "")

        if not session_id:
            return

        # Route to appropriate handler
        if event_type in ("COPY", "PASTE", "CLIPBOARD_TEXT"):
            await self._handle_text_event(event_data)
        elif event_type in ("TAB_SWITCH", "NAVIGATION"):
            await self._handle_navigation_event(event_data)
        elif event_type in ("WINDOW_BLUR", "PAGE_HIDDEN"):
            await self._handle_focus_event(event_data)
        elif event_type == "TRANSFORMER_ALERT":
            await self._handle_transformer_alert(event_data)
        elif event_type in ("FACE_ABSENT", "PHONE_DETECTED"):
            await self._handle_vision_event(event_data)

        # Always update session risk score
        await self._update_session_risk(session_id)

    async def _handle_text_event(self, event_data: Dict[str, Any]):
        """Run transformer analysis on text events (copy/paste)."""
        text = event_data.get("data", {}).get("text", "") or event_data.get("data", {}).get("preview", "")
        session_id = event_data.get("session_id", "")

        if not text or len(text) < 10:
            return

        try:
            # Run similarity check
            from services.similarity import check_text_similarity
            sim_result = await check_text_similarity(text)

            # Run transformer analysis if available
            transformer_result = None
            try:
                from services.transformer_analysis import get_transformer_analyzer
                analyzer = get_transformer_analyzer()
                if analyzer._initialized:
                    # Quick similarity against known sources
                    reference_texts = [
                        "The answer can be found by searching online",
                        "According to the textbook",
                        "Copy and paste from the internet",
                    ]
                    transformer_result = analyzer.check_plagiarism(text, reference_texts)
                    self._stats["transformer_analyses"] += 1
            except Exception as e:
                print(f"[Pipeline] Transformer analysis skipped: {e}")

            # Store result in DB
            async with async_session() as db:
                analysis = AnalysisResult(
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    analysis_type="TEXT_ANALYSIS",
                    similarity_score=sim_result.get("similarity_score", 0),
                    risk_score_added=sim_result.get("risk_score", 0),
                    result_data={
                        "similarity": sim_result,
                        "transformer": transformer_result,
                        "source_text_preview": text[:200],
                    },
                )
                db.add(analysis)
                await db.commit()
                self._stats["db_updates"] += 1

            # Push to WebSocket
            await self._push_to_dashboard(session_id, {
                "type": "text_analysis",
                "similarity_score": sim_result.get("similarity_score", 0),
                "is_suspicious": sim_result.get("is_suspicious", False),
                "transformer_available": transformer_result is not None,
            })

        except Exception as e:
            print(f"[Pipeline] Text analysis error: {e}")

    async def _handle_navigation_event(self, event_data: Dict[str, Any]):
        """Process navigation events - check for forbidden sites."""
        url = event_data.get("data", {}).get("url", "")
        session_id = event_data.get("session_id", "")

        if not url:
            return

        from config import FORBIDDEN_KEYWORDS

        url_lower = url.lower()
        found = [kw for kw in FORBIDDEN_KEYWORDS if kw in url_lower]

        if found:
            async with async_session() as db:
                analysis = AnalysisResult(
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    analysis_type="URL_CHECK",
                    risk_score_added=40,
                    result_data={
                        "url": url,
                        "forbidden_keywords": found,
                    },
                )
                db.add(analysis)

                # Update session
                result = await db.execute(
                    select(ExamSession).where(ExamSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    session.forbidden_site_count += 1
                    session.risk_score = min(100, session.risk_score + 40)
                    session.content_relevance = max(0, session.content_relevance - 20)

                await db.commit()
                self._stats["db_updates"] += 1

            await self._push_to_dashboard(session_id, {
                "type": "forbidden_site",
                "url": url,
                "keywords": found,
            })

    async def _handle_focus_event(self, event_data: Dict[str, Any]):
        """Process window blur / page hidden events."""
        session_id = event_data.get("session_id", "")

        async with async_session() as db:
            result = await db.execute(
                select(ExamSession).where(ExamSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.engagement_score = max(0, session.engagement_score - 3)
                await db.commit()
                self._stats["db_updates"] += 1

    async def _handle_transformer_alert(self, event_data: Dict[str, Any]):
        """Process alerts from the transformer analysis."""
        session_id = event_data.get("session_id", "")
        similarity = event_data.get("data", {}).get("similarity", 0)

        if similarity > 0.7:
            async with async_session() as db:
                result = await db.execute(
                    select(ExamSession).where(ExamSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    session.effort_alignment = max(0, session.effort_alignment - 15)
                    session.risk_score = min(100, session.risk_score + 20)
                    await db.commit()
                    self._stats["db_updates"] += 1

            await self._push_to_dashboard(session_id, {
                "type": "plagiarism_detected",
                "similarity": similarity,
            })

    async def _handle_vision_event(self, event_data: Dict[str, Any]):
        """Process face/phone detection events."""
        session_id = event_data.get("session_id", "")
        event_type = event_data.get("type", "")

        async with async_session() as db:
            result = await db.execute(
                select(ExamSession).where(ExamSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                if event_type == "PHONE_DETECTED":
                    session.risk_score = 100
                    session.risk_level = "suspicious"
                elif event_type == "FACE_ABSENT":
                    session.face_absence_count += 1
                    session.engagement_score = max(0, session.engagement_score - 10)
                await db.commit()
                self._stats["db_updates"] += 1

    async def _update_session_risk(self, session_id: str):
        """Recalculate and update session risk level."""
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(ExamSession).where(ExamSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    # Update risk level based on score
                    if session.risk_score > 85:
                        session.risk_level = "suspicious"
                    elif session.risk_score > 60:
                        session.risk_level = "review"
                    else:
                        session.risk_level = "safe"
                    await db.commit()

                    # Push risk update to dashboard
                    await self._push_to_dashboard(session_id, {
                        "type": "risk_score_update",
                        "risk_score": session.risk_score,
                        "risk_level": session.risk_level,
                        "engagement_score": session.engagement_score,
                        "effort_alignment": session.effort_alignment,
                    })
        except Exception as e:
            print(f"[Pipeline] Risk update error: {e}")

    async def _push_to_dashboard(self, session_id: str, data: Dict[str, Any]):
        """Push real-time update to connected dashboards via WebSocket."""
        try:
            from services.realtime import get_realtime_manager, AlertLevel
            realtime = get_realtime_manager()

            # Get student_id from session
            async with async_session() as db:
                result = await db.execute(
                    select(ExamSession).where(ExamSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                student_id = session.student_id if session else "unknown"

            event_type = data.get("type", "analysis_update")

            # Determine alert level
            alert_level = AlertLevel.INFO
            if data.get("is_suspicious") or data.get("type") == "plagiarism_detected":
                alert_level = AlertLevel.WARNING
            if data.get("type") == "forbidden_site":
                alert_level = AlertLevel.CRITICAL

            await realtime.broadcast_event(
                event_type=event_type,
                student_id=student_id,
                session_id=session_id,
                data=data,
                alert_level=alert_level,
            )
        except Exception as e:
            print(f"[Pipeline] WebSocket push error: {e}")


# Singleton
_pipeline: Optional[AnalysisPipeline] = None


def get_pipeline() -> AnalysisPipeline:
    """Get or create the analysis pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline()
    return _pipeline
