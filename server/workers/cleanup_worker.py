"""Scheduled cleanup: retention policies and stale sessions."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from workers.celery_app import celery_app
from supabase_client import get_supabase


@celery_app.task(name="workers.cleanup_worker.run_retention_cleanup")
def run_retention_cleanup() -> dict:
    sb = get_supabase()
    if not sb:
        return {"status": "skipped", "reason": "no database"}

    now = datetime.now(timezone.utc)
    deleted_screenshots = 0
    scrubbed_events = 0

    sessions_res = sb.table("sessions").select("id, consent_metadata, created_at").execute()
    for session in sessions_res.data or []:
        meta = session.get("consent_metadata") or {}
        mode = meta.get("retention_mode", "standard")
        days = 90 if mode == "extended" else 30
        cutoff = now - timedelta(days=days)

        created = session.get("created_at")
        if not created:
            continue
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_dt > cutoff:
            continue

        events_res = sb.table("v2_events").select("id, screenshot_url").eq("session_id", session["id"]).execute()
        for event in events_res.data or []:
            url = event.get("screenshot_url")
            if url:
                sb.table("v2_events").update({"screenshot_url": None}).eq("id", event["id"]).execute()
                scrubbed_events += 1
                deleted_screenshots += 1

    derived_cutoff = now - timedelta(days=365)
    return {
        "status": "ok",
        "scrubbed_screenshot_refs": scrubbed_events,
        "derived_cutoff": derived_cutoff.isoformat(),
    }


@celery_app.task(name="workers.cleanup_worker.terminate_stale_sessions")
def terminate_stale_sessions(max_hours: int = 8) -> dict:
    sb = get_supabase()
    if not sb:
        return {"status": "skipped"}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
    res = sb.table("sessions").select("id, started_at").eq("status", "active").execute()
    terminated = 0

    for session in res.data or []:
        started = session.get("started_at")
        if not started:
            continue
        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if started_dt < cutoff:
            sb.table("sessions").update({
                "status": "terminated",
                "ended_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", session["id"]).execute()
            terminated += 1

    return {"status": "ok", "terminated": terminated}
