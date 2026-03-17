"""
ExamGuard Pro - Transformer Endpoint
API routes for Transformer-based analysis (URL, behavioral, screen content)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class URLClassifyRequest(BaseModel):
    url: str


class BehaviorAnalysisRequest(BaseModel):
    events: List[Dict[str, Any]]


class ScreenContentRequest(BaseModel):
    text: str


class BatchURLRequest(BaseModel):
    urls: List[str]


@router.post("/classify-url")
async def classify_url(request: URLClassifyRequest):
    """Classify a URL into a risk category using the transformer model."""
    from services.transformer_analysis import get_transformer_analyzer

    analyzer = get_transformer_analyzer()
    result = analyzer.classify_url(request.url)
    return result


@router.post("/analyze-behavior")
async def analyze_behavior(request: BehaviorAnalysisRequest):
    """
    Analyze a sequence of student events for anomalous behavior.
    Events should have 'type' and 'timestamp' fields.
    """
    from services.transformer_analysis import get_transformer_analyzer

    analyzer = get_transformer_analyzer()

    if not request.events:
        raise HTTPException(status_code=400, detail="No events provided")

    result = analyzer.predict_behavior_risk(request.events)
    return result


@router.post("/classify-screen")
async def classify_screen_content(request: ScreenContentRequest):
    """Classify screenshot/OCR text into a risk category."""
    from services.transformer_analysis import get_transformer_analyzer

    analyzer = get_transformer_analyzer()

    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")

    result = analyzer.classify_screen_content(request.text)
    return result


@router.post("/batch-classify-urls")
async def batch_classify_urls(request: BatchURLRequest):
    """Classify multiple URLs at once."""
    from services.transformer_analysis import get_transformer_analyzer

    analyzer = get_transformer_analyzer()
    results = []
    for url in request.urls:
        result = analyzer.classify_url(url)
        results.append(result)
    return {"results": results, "total": len(results)}


@router.get("/status")
async def transformer_status():
    """Get Transformer analyzer status."""
    from services.transformer_analysis import get_transformer_analyzer

    analyzer = get_transformer_analyzer()
    return analyzer.get_status()
