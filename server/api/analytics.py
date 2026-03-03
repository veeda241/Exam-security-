"""
ExamGuard Pro - Advanced Analytics API
Endpoints for local ML services: Biometrics, Gaze, Forensics, Audio.

All processing runs 100% locally - no external API calls.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64
import numpy as np

from services import (
    get_biometrics_service,
    get_gaze_service,
    get_forensics_service,
    get_audio_service,
)

router = APIRouter(prefix="/api/analytics", tags=["Advanced Analytics"])


# =============================================================================
# Request/Response Models
# =============================================================================

class KeystrokeEventData(BaseModel):
    """Keystroke event from client"""
    key: str
    timestamp: float
    event_type: str = "keydown"  # keydown or keyup


class MouseEventData(BaseModel):
    """Mouse event from client"""
    x: float
    y: float
    timestamp: float
    event_type: str = "move"  # move, click, scroll
    button: Optional[int] = None
    scroll_delta: Optional[float] = None


class BiometricsRequest(BaseModel):
    """Biometrics analysis request"""
    student_id: str
    session_id: str
    events: List[Dict[str, Any]]


class GazeDataRequest(BaseModel):
    """Gaze data from client-side tracking"""
    student_id: str
    session_id: str
    gaze_points: List[Dict[str, float]]  # [{x, y, timestamp, confidence}]


class ForensicsRequest(BaseModel):
    """Browser forensics data"""
    student_id: str
    session_id: str
    data: Dict[str, Any]  # Browser fingerprint and indicators


class AudioRequest(BaseModel):
    """Audio analysis request"""
    student_id: str
    session_id: str
    audio_base64: str  # Base64 encoded audio
    format_type: str = "pcm16"
    sample_rate: int = 44100


class AnalyticsResponse(BaseModel):
    """Standard analytics response"""
    success: bool
    student_id: str
    timestamp: str
    data: Dict[str, Any]
    alerts: List[str] = []
    risk_score: float = 0.0


# =============================================================================
# Biometrics Endpoints
# =============================================================================

@router.post("/biometrics/analyze", response_model=AnalyticsResponse)
async def analyze_biometrics(request: BiometricsRequest):
    """
    Analyze behavioral biometrics (keystroke + mouse dynamics).
    
    Processes events and returns:
    - Keystroke pattern analysis
    - Mouse behavior analysis
    - Identity verification score
    - Behavioral anomalies
    """
    service = get_biometrics_service()
    
    # Process each event
    for event in request.events:
        service.process_event(request.student_id, event)
    
    # Get full analysis
    analysis = service.get_full_analysis(request.student_id)
    
    return AnalyticsResponse(
        success=True,
        student_id=request.student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "keystroke": analysis.get("keystroke", {}),
            "mouse": analysis.get("mouse", {}),
            "scroll": analysis.get("scroll", {}),
            "identity_match": analysis.get("identity_match", 1.0),
            "anomaly_score": analysis.get("anomaly_score", 0),
        },
        alerts=analysis.get("alerts", []),
        risk_score=analysis.get("anomaly_score", 0),
    )


@router.post("/biometrics/baseline", response_model=AnalyticsResponse)
async def create_biometrics_baseline(request: BiometricsRequest):
    """
    Create baseline biometric profile for identity verification.
    
    Should be called at the start of an exam to establish
    the student's unique behavioral patterns.
    """
    service = get_biometrics_service()
    
    # Process events first
    for event in request.events:
        service.process_event(request.student_id, event)
    
    # Create baseline
    profile = service.create_baseline_profile(request.student_id)
    
    if profile:
        return AnalyticsResponse(
            success=True,
            student_id=request.student_id,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "baseline_created": True,
                "profile_summary": {
                    "keystroke_samples": len(profile.keystroke_timings) if hasattr(profile, 'keystroke_timings') else 0,
                    "mouse_samples": len(profile.mouse_speeds) if hasattr(profile, 'mouse_speeds') else 0,
                }
            },
            alerts=[],
            risk_score=0,
        )
    else:
        return AnalyticsResponse(
            success=False,
            student_id=request.student_id,
            timestamp=datetime.utcnow().isoformat(),
            data={"baseline_created": False, "error": "Insufficient data for baseline"},
            alerts=["Need more behavioral samples to create baseline"],
            risk_score=0,
        )


@router.get("/biometrics/{student_id}", response_model=AnalyticsResponse)
async def get_biometrics_analysis(student_id: str):
    """Get current biometrics analysis for a student"""
    service = get_biometrics_service()
    analysis = service.get_full_analysis(student_id)
    
    return AnalyticsResponse(
        success=True,
        student_id=student_id,
        timestamp=datetime.utcnow().isoformat(),
        data=analysis,
        alerts=analysis.get("alerts", []),
        risk_score=analysis.get("anomaly_score", 0),
    )


# =============================================================================
# Gaze Tracking Endpoints
# =============================================================================

@router.post("/gaze/analyze", response_model=AnalyticsResponse)
async def analyze_gaze(request: GazeDataRequest):
    """
    Analyze gaze/eye tracking data.
    
    Processes gaze points and returns:
    - Attention score
    - Time in each screen zone
    - Distraction count
    - Looking away duration
    - Suspicious patterns
    """
    service = get_gaze_service()
    
    # Process each gaze point
    for point in request.gaze_points:
        service.process_gaze_data(request.student_id, point)
    
    # Get analysis
    analysis = service.get_analysis(request.student_id)
    
    return AnalyticsResponse(
        success=True,
        student_id=request.student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "current_gaze": {"x": analysis.current_gaze_x, "y": analysis.current_gaze_y},
            "looking_at_screen": analysis.looking_at_screen,
            "attention_score": analysis.attention_score,
            "distraction_count": analysis.distraction_count,
            "looking_away_duration_ms": analysis.looking_away_duration_ms,
            "rapid_eye_movement_count": analysis.rapid_eye_movement_count,
            "reading_pattern_detected": analysis.reading_pattern_detected,
            "current_zone": analysis.current_zone,
            "time_in_zones": analysis.time_in_zones,
        },
        alerts=analysis.anomalies,
        risk_score=analysis.anomaly_score,
    )


@router.get("/gaze/{student_id}/heatmap")
async def get_gaze_heatmap(student_id: str):
    """
    Get attention heatmap for visualization.
    
    Returns a 10x10 grid showing where the student
    has been looking during the exam.
    """
    service = get_gaze_service()
    heatmap = service.get_heatmap(student_id)
    
    return {
        "success": True,
        "student_id": student_id,
        "heatmap": heatmap,
    }


@router.get("/gaze/{student_id}", response_model=AnalyticsResponse)
async def get_gaze_analysis(student_id: str):
    """Get current gaze analysis for a student"""
    service = get_gaze_service()
    analysis = service.get_analysis(student_id)
    
    return AnalyticsResponse(
        success=True,
        student_id=student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "attention_score": analysis.attention_score,
            "looking_at_screen": analysis.looking_at_screen,
            "distraction_count": analysis.distraction_count,
            "current_zone": analysis.current_zone,
        },
        alerts=analysis.anomalies,
        risk_score=analysis.anomaly_score,
    )


# =============================================================================
# Browser Forensics Endpoints
# =============================================================================

@router.post("/forensics/analyze", response_model=AnalyticsResponse)
async def analyze_forensics(request: ForensicsRequest):
    """
    Analyze browser forensics data.
    
    Detects:
    - Virtual machines
    - Remote desktop sessions
    - Suspicious browser extensions
    - Screen sharing
    - Browser fingerprint changes
    """
    service = get_forensics_service()
    analysis = service.analyze(request.student_id, request.data)
    
    return AnalyticsResponse(
        success=True,
        student_id=request.student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "vm_detection": {
                "is_vm": analysis.vm_detection.is_vm,
                "confidence": analysis.vm_detection.confidence,
                "vm_type": analysis.vm_detection.vm_type,
                "indicators": analysis.vm_detection.indicators,
            },
            "remote_desktop": {
                "is_remote": analysis.remote_desktop.is_remote,
                "confidence": analysis.remote_desktop.confidence,
                "remote_type": analysis.remote_desktop.remote_type,
                "indicators": analysis.remote_desktop.indicators,
            },
            "extensions": {
                "suspicious_count": analysis.extensions.suspicious_count,
                "risk_level": analysis.extensions.risk_level,
                "extensions": analysis.extensions.extensions,
            },
            "screen_share": {
                "is_sharing": analysis.screen_share.is_sharing,
                "confidence": analysis.screen_share.confidence,
                "indicators": analysis.screen_share.indicators,
            },
            "fingerprint": {
                "user_agent": analysis.fingerprint.user_agent[:100] if analysis.fingerprint.user_agent else "",
                "platform": analysis.fingerprint.platform,
                "screen": f"{analysis.fingerprint.screen_width}x{analysis.fingerprint.screen_height}",
                "webgl_renderer": analysis.fingerprint.webgl_renderer[:50] if analysis.fingerprint.webgl_renderer else "",
            },
        },
        alerts=analysis.alerts,
        risk_score=analysis.overall_risk_score,
    )


@router.get("/forensics/alerts")
async def get_all_forensics_alerts():
    """Get all current forensics alerts by student"""
    service = get_forensics_service()
    alerts = service.get_all_alerts()
    
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "alerts": alerts,
        "total_alerts": sum(len(a) for a in alerts.values()),
    }


# =============================================================================
# Audio Analysis Endpoints
# =============================================================================

@router.post("/audio/analyze", response_model=AnalyticsResponse)
async def analyze_audio(request: AudioRequest):
    """
    Analyze audio for suspicious patterns.
    
    Detects:
    - Voice presence
    - Multiple speakers
    - Synthetic/TTS voice
    - Background noise anomalies
    - Sudden audio changes
    """
    service = get_audio_service()
    
    # Decode base64 audio
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {e}")
    
    # Analyze
    analysis = service.process_audio(
        request.student_id,
        audio_bytes,
        request.format_type
    )
    
    return AnalyticsResponse(
        success=True,
        student_id=request.student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "voice_detection": {
                "is_voice_present": analysis.voice_detection.is_voice_present,
                "voice_count": analysis.voice_detection.voice_count_estimate,
                "voice_type": analysis.voice_detection.voice_type,
                "confidence": analysis.voice_detection.confidence,
            },
            "background_noise": {
                "noise_level": analysis.background_noise.noise_level,
                "noise_type": analysis.background_noise.noise_type,
                "is_consistent": analysis.background_noise.is_consistent,
                "sudden_changes": analysis.background_noise.sudden_changes,
            },
            "suspicious_events": [
                {
                    "type": e.event_type,
                    "confidence": e.confidence,
                    "description": e.description,
                }
                for e in analysis.suspicious_events
            ],
        },
        alerts=analysis.alerts,
        risk_score=analysis.anomaly_score,
    )


@router.post("/audio/analyze-samples")
async def analyze_audio_samples(
    student_id: str = Body(...),
    samples: List[float] = Body(..., description="Audio samples as float array"),
):
    """
    Analyze audio samples directly (no base64 encoding).
    
    Useful for real-time audio streaming.
    """
    service = get_audio_service()
    
    # Convert to numpy array
    samples_np = np.array(samples, dtype=np.float64)
    
    # Analyze
    analysis = service.analyze_samples(student_id, samples_np)
    
    return AnalyticsResponse(
        success=True,
        student_id=student_id,
        timestamp=datetime.utcnow().isoformat(),
        data={
            "voice_detected": analysis.voice_detection.is_voice_present,
            "anomaly_score": analysis.anomaly_score,
            "is_suspicious": analysis.is_suspicious,
        },
        alerts=analysis.alerts,
        risk_score=analysis.anomaly_score,
    )


# =============================================================================
# Combined Analytics Endpoint
# =============================================================================

@router.get("/combined/{student_id}")
async def get_combined_analytics(student_id: str):
    """
    Get combined analytics from all services for a student.
    
    Returns a unified view of:
    - Biometrics analysis
    - Gaze tracking
    - Forensics
    - Audio analysis
    """
    biometrics = get_biometrics_service().get_full_analysis(student_id)
    gaze = get_gaze_service().get_analysis(student_id)
    forensics_history = get_forensics_service().get_history(student_id)
    audio_history = get_audio_service().get_history(student_id)
    
    # Calculate combined risk score
    combined_risk = 0.0
    all_alerts = []
    
    # Biometrics contribution
    bio_risk = biometrics.get("anomaly_score", 0)
    combined_risk += bio_risk * 0.25
    all_alerts.extend(biometrics.get("alerts", []))
    
    # Gaze contribution
    gaze_risk = gaze.anomaly_score
    combined_risk += gaze_risk * 0.25
    all_alerts.extend(gaze.anomalies)
    
    # Forensics contribution
    if forensics_history:
        forensics_risk = forensics_history[-1].overall_risk_score
        combined_risk += forensics_risk * 0.30
        all_alerts.extend(forensics_history[-1].alerts)
    
    # Audio contribution
    if audio_history:
        audio_risk = audio_history[-1].anomaly_score
        combined_risk += audio_risk * 0.20
        all_alerts.extend(audio_history[-1].alerts)
    
    return {
        "success": True,
        "student_id": student_id,
        "timestamp": datetime.utcnow().isoformat(),
        "combined_risk_score": min(100, combined_risk),
        "alerts": list(set(all_alerts)),  # Remove duplicates
        "components": {
            "biometrics": {
                "risk_score": bio_risk,
                "identity_match": biometrics.get("identity_match", 1.0),
            },
            "gaze": {
                "risk_score": gaze_risk,
                "attention_score": gaze.attention_score,
                "looking_at_screen": gaze.looking_at_screen,
            },
            "forensics": {
                "risk_score": forensics_history[-1].overall_risk_score if forensics_history else 0,
                "vm_detected": forensics_history[-1].vm_detection.is_vm if forensics_history else False,
                "remote_detected": forensics_history[-1].remote_desktop.is_remote if forensics_history else False,
            },
            "audio": {
                "risk_score": audio_history[-1].anomaly_score if audio_history else 0,
                "voice_detected": audio_history[-1].voice_detection.is_voice_present if audio_history else False,
            },
        },
    }


# =============================================================================
# Service Status
# =============================================================================

@router.get("/status")
async def get_analytics_status():
    """Get status of all analytics services"""
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "biometrics": {"status": "active", "type": "local"},
            "gaze_tracking": {"status": "active", "type": "local"},
            "browser_forensics": {"status": "active", "type": "local"},
            "audio_analysis": {"status": "active", "type": "local"},
        },
        "note": "All services run 100% locally - no external API calls",
    }
