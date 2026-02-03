"""
ExamGuard Pro - Text Similarity Module
Uses Sentence-BERT for comparing answer text against known sources
"""

import asyncio
from typing import Dict, Any, List, Optional
from config import TEXT_SIMILARITY_THRESHOLD

# Try to import sentence-transformers, fallback if not available
try:
    from sentence_transformers import SentenceTransformer, util
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("[WARN] sentence-transformers not installed. Text similarity will use fallback mode.")


class TextSimilarityChecker:
    """Text similarity analysis using Sentence-BERT"""
    
    def __init__(self):
        if SBERT_AVAILABLE:
            # Use a lightweight model for speed
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.model = None
        
        # Knowledge base of common cheating sources
        self.reference_texts = [
            "The answer to this question can be found by...",
            "According to the textbook...",
            "As stated in the lecture notes...",
        ]
        self._reference_embeddings = None
    
    def _get_reference_embeddings(self):
        """Get embeddings for reference texts (lazy loading)"""
        if self._reference_embeddings is None and self.model:
            self._reference_embeddings = self.model.encode(
                self.reference_texts, 
                convert_to_tensor=True
            )
        return self._reference_embeddings
    
    def check_similarity(
        self, 
        text: str, 
        compare_texts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check text similarity against reference texts
        
        Args:
            text: The text to analyze
            compare_texts: Optional list of texts to compare against
        """
        
        if not SBERT_AVAILABLE:
            return self._fallback_check(text)
        
        if not text or len(text) < 20:
            return {
                "similarity_score": 0,
                "is_suspicious": False,
                "matched_text": None,
                "warning": "Text too short for analysis",
            }
        
        try:
            # Encode the input text
            text_embedding = self.model.encode(text, convert_to_tensor=True)
            
            # Get reference embeddings
            if compare_texts:
                reference_embeddings = self.model.encode(compare_texts, convert_to_tensor=True)
            else:
                reference_embeddings = self._get_reference_embeddings()
            
            if reference_embeddings is None:
                return {
                    "similarity_score": 0,
                    "is_suspicious": False,
                    "matched_text": None,
                    "warning": "No reference texts available",
                }
            
            # Calculate cosine similarity
            similarities = util.cos_sim(text_embedding, reference_embeddings)
            
            # Get max similarity
            max_similarity = float(similarities.max())
            max_index = int(similarities.argmax())
            
            texts = compare_texts if compare_texts else self.reference_texts
            matched_text = texts[max_index] if max_index < len(texts) else None
            
            is_suspicious = max_similarity >= TEXT_SIMILARITY_THRESHOLD
            
            return {
                "similarity_score": max_similarity,
                "is_suspicious": is_suspicious,
                "matched_text": matched_text[:200] if matched_text else None,
                "threshold": TEXT_SIMILARITY_THRESHOLD,
                "risk_score": 30 if is_suspicious else 0,
            }
            
        except Exception as e:
            return {
                "similarity_score": 0,
                "is_suspicious": False,
                "matched_text": None,
                "error": str(e),
            }
    
    def _fallback_check(self, text: str) -> Dict[str, Any]:
        """Fallback when sentence-transformers is not available"""
        # Simple keyword matching as fallback
        suspicious_phrases = [
            "copy paste",
            "copied from",
            "according to google",
            "i found online",
        ]
        
        text_lower = text.lower()
        found = any(phrase in text_lower for phrase in suspicious_phrases)
        
        return {
            "similarity_score": 0.8 if found else 0,
            "is_suspicious": found,
            "matched_text": None,
            "method": "keyword_fallback",
            "warning": "Using keyword fallback - sentence-transformers not installed",
        }
    
    def add_reference_texts(self, texts: List[str]):
        """Add texts to the reference database"""
        self.reference_texts.extend(texts)
        self._reference_embeddings = None  # Reset embeddings


# Global checker instance
_checker = None


def get_checker() -> TextSimilarityChecker:
    """Get or create text similarity checker"""
    global _checker
    if _checker is None:
        _checker = TextSimilarityChecker()
    return _checker


async def check_text_similarity(
    text: str,
    compare_texts: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Check text similarity (async wrapper)
    
    Args:
        text: The text to analyze
        compare_texts: Optional list of texts to compare against
        
    Returns:
        Dictionary with similarity results:
        - similarity_score: float (0-1)
        - is_suspicious: bool
        - matched_text: str (if suspicious)
        - risk_score: float
    """
    checker = get_checker()
    
    # Run in thread pool to not block
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, 
        checker.check_similarity, 
        text, 
        compare_texts
    )
    
    return result
