"""Shared worker utilities: DB writes, risk recompute, Redis publish."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

import redis

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from core.risk_engine import Event, RiskConfig, compute_risk
from supabase_client import get_supabase


def _redis_client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


def get_active_risk_config() -> RiskConfig:
    sb = get_supabase()
    if sb:
        res = sb.table("risk_configs").select("*").eq("active", True).limit(1).execute()
        if res.data:
            row = res.data[0]
            return RiskConfig(weights=row["weights"], thresholds=row["thresholds"])
    return RiskConfig.default()


def insert_event(
    session_id: str,
    event_type: str,
    payload: dict[str, Any],
    weight: float = 0,
    screenshot_url: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    sb = get_supabase()
    if not sb:
        return None

    config = get_active_risk_config()
    if weight <= 0:
        weight = float(config.weights.get(event_type, 0))

    row = {
        "session_id": session_id,
        "type": event_type,
        "payload": payload,
        "weight": weight,
        "screenshot_url": screenshot_url,
    }
    res = sb.table("v2_events").insert(row).execute()
    if not res.data:
        return None
    return res.data[0]


def publish_session_message(session_id: str, message: dict[str, Any]) -> None:
    client = _redis_client()
    client.publish(f"session:{session_id}", json.dumps(message))


def recompute_and_update_session_risk(session_id: str) -> dict[str, Any]:
    sb = get_supabase()
    config = get_active_risk_config()

    if not sb:
        return {"score": 0, "level": "safe", "breakdown": {}}

    events_res = sb.table("v2_events").select("type, weight").eq("session_id", session_id).execute()
    events = [Event(type=r["type"], weight=float(r.get("weight") or 0)) for r in (events_res.data or [])]
    result = compute_risk(events, config)

    sb.table("sessions").update({
        "risk_score": result.score,
        "risk_level": result.level,
    }).eq("id", session_id).execute()

    publish_session_message(session_id, {
        "type": "risk_update",
        "session_id": session_id,
        "score": result.score,
        "level": result.level,
        "breakdown": result.breakdown,
    })

    return {"score": result.score, "level": result.level, "breakdown": result.breakdown}


def finalize_worker_result(
    session_id: str,
    event_type: str,
    payload: dict[str, Any],
    weight: float = 0,
) -> dict[str, Any]:
    event = insert_event(session_id, event_type, payload, weight=weight)
    if event:
        publish_session_message(session_id, {
            "type": "event",
            "session_id": session_id,
            "event": event,
        })
    risk = recompute_and_update_session_risk(session_id)
    return {"event": event, "risk": risk}
