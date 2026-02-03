"""
ExamGuard Pro - Transformer Endpoint
API routes for Transformer-based text analysis
"""

from fastapi import APIRouter, HTTPException

from api.schemas import (
    TextAnalysisRequest,
    PlagiarismCheckRequest,
    MultiAnswerRequest
)

router = APIRouter()


@router.post("/similarity")
async def transformer_similarity_check(request: TextAnalysisRequest):
    """
    Check text similarity using Transformer model.
    
    Use for comparing student answers against reference materials.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    if not request.compare_texts:
        return {
            "error": "No comparison texts provided",
            "status": analyzer.get_status()
        }
    
    results = []
    for compare_text in request.compare_texts:
        result = analyzer.compute_similarity(request.text, compare_text)
        results.append({
            "compare_text_preview": compare_text[:100] + "..." if len(compare_text) > 100 else compare_text,
            **result
        })
    
    # Find max similarity
    max_sim = max(r.get("similarity", 0) for r in results)
    
    return {
        "results": results,
        "max_similarity": round(max_sim, 4),
        "is_suspicious": max_sim > 0.7,
        "analyzer_status": analyzer.get_status()
    }


@router.post("/plagiarism")
async def transformer_plagiarism_check(request: PlagiarismCheckRequest):
    """
    Check for potential plagiarism in student answer.
    
    Compares answer against known reference texts.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    result = analyzer.check_plagiarism(
        request.answer_text,
        request.reference_texts,
        request.threshold
    )
    
    return {
        **result,
        "analyzer_status": analyzer.get_status()
    }


@router.post("/cross-compare")
async def transformer_cross_compare(request: MultiAnswerRequest):
    """
    Compare multiple student answers to detect potential copying.
    
    Useful for detecting collusion between students.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    if len(request.answers) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 answers required for comparison"
        )
    
    result = analyzer.analyze_answer_patterns(request.answers)
    
    return {
        **result,
        "analyzer_status": analyzer.get_status()
    }


@router.get("/status")
async def transformer_status():
    """Get Transformer analyzer status."""
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    return analyzer.get_status()


@router.post("/encode")
async def encode_text(text: str):
    """
    Encode text using Transformer encoder.
    
    Returns the embedding vector for the input text.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    # Get embedding
    embedding = analyzer._get_embedding(text)
    
    if embedding is None:
        raise HTTPException(status_code=500, detail="Failed to encode text")
    
    return {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "embedding_dim": len(embedding),
        "embedding": embedding[:10],  # Return first 10 dims as preview
        "status": analyzer.get_status()
    }


@router.post("/batch-compare")
async def batch_compare(texts: list[str], reference: str):
    """
    Compare multiple texts against a single reference.
    
    Efficient batch comparison for grading scenarios.
    """
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    
    results = []
    for i, text in enumerate(texts):
        result = analyzer.compute_similarity(text, reference)
        results.append({
            "index": i,
            "text_preview": text[:50] + "..." if len(text) > 50 else text,
            **result
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    
    return {
        "reference_preview": reference[:100] + "..." if len(reference) > 100 else reference,
        "total_compared": len(results),
        "results": results,
        "analyzer_status": analyzer.get_status()
    }
