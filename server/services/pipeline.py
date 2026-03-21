import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from supabase_client import get_supabase

supabase = get_supabase()

class AnalysisPipeline:
    """
    Real-time analysis pipeline using Supabase.
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
        """Run transformer analysis on text events via Supabase."""
        text = event_data.get("data", {}).get("text", "") or event_data.get("data", {}).get("preview", "")
        session_id = event_data.get("session_id", "")
        event_type = event_data.get("type", "")

        # Update copy_count in Supabase for COPY/PASTE events
        if event_type in ("COPY", "PASTE"):
            try:
                res = supabase.table("exam_sessions").select("copy_count, risk_score, effort_alignment").eq("id", session_id).execute()
                if res.data:
                    session = res.data[0]
                    updates = {
                        "copy_count": session.get("copy_count", 0) + 1,
                        "risk_score": min(100, session.get("risk_score", 0) + 8),
                        "effort_alignment": max(0, session.get("effort_alignment", 100) - 5),
                    }
                    supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
                    self._stats["db_updates"] += 1
            except Exception as e:
                print(f"[Pipeline] Copy count update error: {e}")

        if not text or len(text) < 10:
            return

        try:
            from services.similarity import check_text_similarity
            sim_result = await check_text_similarity(text)

            transformer_result = None
            try:
                from services.transformer_analysis import get_transformer_analyzer
                analyzer = get_transformer_analyzer()
                if analyzer._screen_initialized:
                    transformer_result = analyzer.classify_screen_content(text)
                    self._stats["transformer_analyses"] += 1
            except Exception as e:
                print(f"[Pipeline] Transformer analysis skipped: {e}")

            # Store result in Supabase
            analysis = {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "analysis_type": "TEXT_ANALYSIS",
                "similarity_score": sim_result.get("similarity_score", 0),
                "risk_score_added": sim_result.get("risk_score", 0),
                "result_data": {
                    "similarity": sim_result,
                    "transformer": transformer_result,
                    "source_text_preview": text[:200],
                },
            }
            supabase.table("analysis_results").insert(analysis).execute()
            self._stats["db_updates"] += 1

            await self._push_to_dashboard(session_id, {
                "type": "text_analysis",
                "similarity_score": sim_result.get("similarity_score", 0),
                "is_suspicious": sim_result.get("is_suspicious", False),
                "transformer_available": transformer_result is not None,
            })

        except Exception as e:
            print(f"[Pipeline] Text analysis error: {e}")

    async def _handle_navigation_event(self, event_data: Dict[str, Any]):
        """Process navigation events via Supabase."""
        url = event_data.get("data", {}).get("url", "")
        session_id = event_data.get("session_id", "")

        if not url:
            return

        # Every tab switch / navigation reduces engagement and bumps risk slightly
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            return
        session = res.data[0]

        updates = {
            "tab_switch_count": session.get("tab_switch_count", 0) + 1,
            "engagement_score": max(0, session.get("engagement_score", 100) - 2),
            "risk_score": min(100, session.get("risk_score", 0) + 5),
        }

        from config import FORBIDDEN_KEYWORDS
        url_lower = url.lower()
        found = [kw for kw in FORBIDDEN_KEYWORDS if kw in url_lower]

        if found:
            analysis = {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "analysis_type": "URL_CHECK",
                "risk_score_added": 40,
                "result_data": {
                    "url": url,
                    "forbidden_keywords": found,
                },
            }
            supabase.table("analysis_results").insert(analysis).execute()

            # Extra penalties for forbidden sites
            updates["forbidden_site_count"] = session.get("forbidden_site_count", 0) + 1
            updates["risk_score"] = min(100, session.get("risk_score", 0) + 40)
            updates["content_relevance"] = max(0, session.get("content_relevance", 100) - 20)
            updates["engagement_score"] = max(0, session.get("engagement_score", 100) - 10)

            await self._push_to_dashboard(session_id, {
                "type": "forbidden_site",
                "url": url,
                "keywords": found,
            })

        supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
        self._stats["db_updates"] += 1

    async def _handle_focus_event(self, event_data: Dict[str, Any]):
        """Process window blur via Supabase."""
        session_id = event_data.get("session_id", "")
        res = supabase.table("exam_sessions").select("engagement_score, risk_score").eq("id", session_id).execute()
        if res.data:
            session = res.data[0]
            updates = {
                "engagement_score": max(0, session.get("engagement_score", 100) - 3),
                "risk_score": min(100, session.get("risk_score", 0) + 3),
            }
            supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
            self._stats["db_updates"] += 1

    async def _handle_transformer_alert(self, event_data: Dict[str, Any]):
        """Process transformer alerts via Supabase."""
        session_id = event_data.get("session_id", "")
        similarity = event_data.get("data", {}).get("similarity", 0)

        if similarity > 0.7:
            res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
            if res.data:
                session = res.data[0]
                updates = {
                    "effort_alignment": max(0, session.get("effort_alignment", 100) - 15),
                    "risk_score": min(100, session.get("risk_score", 0) + 20)
                }
                supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
                self._stats["db_updates"] += 1

            await self._push_to_dashboard(session_id, {
                "type": "plagiarism_detected",
                "similarity": similarity,
            })

    async def _handle_vision_event(self, event_data: Dict[str, Any]):
        """Process vision events via Supabase."""
        session_id = event_data.get("session_id", "")
        event_type = event_data.get("type", "")

        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if res.data:
            session = res.data[0]
            updates = {}
            if event_type == "PHONE_DETECTED":
                updates["risk_score"] = 100
                updates["risk_level"] = "suspicious"
            elif event_type == "FACE_ABSENT":
                updates["face_absence_count"] = session.get("face_absence_count", 0) + 1
                updates["engagement_score"] = max(0, session.get("engagement_score", 100) - 10)
            
            if updates:
                supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
                self._stats["db_updates"] += 1

    async def _update_session_risk(self, session_id: str):
        """Update session risk level in Supabase."""
        try:
            res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
            if res.data:
                session = res.data[0]
                risk_score = session.get("risk_score", 0)
                
                if risk_score > 85:
                    new_level = "suspicious"
                elif risk_score > 60:
                    new_level = "review"
                else:
                    new_level = "safe"
                
                if session.get("risk_level") != new_level:
                    supabase.table("exam_sessions").update({"risk_level": new_level}).eq("id", session_id).execute()

                await self._push_to_dashboard(session_id, {
                    "type": "risk_score_update",
                    "risk_score": risk_score,
                    "risk_level": new_level,
                    "engagement_score": session.get("engagement_score"),
                    "effort_alignment": session.get("effort_alignment"),
                })
        except Exception as e:
            print(f"[Pipeline] Risk update error: {e}")

    async def _push_to_dashboard(self, session_id: str, data: Dict[str, Any]):
        """Push real-time update to dashboards via WebSocket."""
        try:
            from services.realtime import get_realtime_manager, AlertLevel
            realtime = get_realtime_manager()

            res = supabase.table("exam_sessions").select("student_id").eq("id", session_id).execute()
            student_id = res.data[0].get("student_id", "unknown") if res.data else "unknown"

            event_type = data.get("type", "analysis_update")
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
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline()
    return _pipeline
