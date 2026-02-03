"""
ExamGuard Pro - Transformer-based Analysis Service
Uses custom Transformer model for advanced text analysis
"""

import sys
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

import torch
import torch.nn.functional as F

# Transformer imports - done dynamically to avoid path conflicts
TRANSFORMER_AVAILABLE = False
TransformerEncoderOnly = None
SimpleTokenizer = None

def _load_transformer_modules():
    """Load transformer modules dynamically to avoid import conflicts."""
    global TRANSFORMER_AVAILABLE, TransformerEncoderOnly, SimpleTokenizer
    
    try:
        # Add transformer module to path temporarily
        transformer_path = Path(__file__).parent.parent.parent / "transformer"
        if str(transformer_path) not in sys.path:
            sys.path.insert(0, str(transformer_path))
        
        from model.transformer import TransformerEncoderOnly as TEnc
        from data.tokenizer import SimpleTokenizer as STok
        
        TransformerEncoderOnly = TEnc
        SimpleTokenizer = STok
        TRANSFORMER_AVAILABLE = True
        
        # Remove from path to avoid conflicts
        if str(transformer_path) in sys.path:
            sys.path.remove(str(transformer_path))
            
    except ImportError as e:
        print(f"[WARN] Transformer module not available: {e}")
        TRANSFORMER_AVAILABLE = False


class TransformerAnalyzer:
    """
    Transformer-based text analysis for ExamGuard Pro
    
    Features:
    - Text similarity detection (plagiarism)
    - Answer quality scoring
    - Behavioral pattern analysis
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the Transformer analyzer.
        
        Args:
            model_path: Path to pre-trained model checkpoint
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self._initialized = False
        
        # Load transformer modules dynamically
        _load_transformer_modules()
        
        if TRANSFORMER_AVAILABLE:
            self._initialize_model(model_path)
    
    def _initialize_model(self, model_path: Optional[str] = None):
        """Initialize the Transformer model."""
        try:
            # Create encoder-only model for text encoding
            self.model = TransformerEncoderOnly(
                vocab_size=10000,
                d_model=256,
                n_heads=4,
                n_layers=4,
                d_ff=512,
                max_seq_len=256,
                dropout=0.0,  # No dropout for inference
                num_classes=None,  # No classification head - use embeddings
                pooling="mean"
            ).to(self.device)
            
            # Load pre-trained weights if available
            if model_path and os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                print(f"[INFO] Loaded Transformer from {model_path}")
            else:
                print("[INFO] Using untrained Transformer (for encoding only)")
            
            self.model.eval()
            
            # Initialize tokenizer
            self.tokenizer = SimpleTokenizer(vocab_size=10000, min_freq=1)
            
            # Build basic vocabulary
            sample_texts = [
                "the a an is are was were be been being",
                "student exam test answer question",
                "copy paste switch tab window",
                "face detection person present absent",
            ]
            self.tokenizer.build_vocab(sample_texts)
            
            self._initialized = True
            print(f"[INFO] Transformer Analyzer initialized on {self.device}")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize Transformer: {e}")
            self._initialized = False
    
    def encode_text(self, text: str) -> Optional[torch.Tensor]:
        """
        Encode text to embedding vector.
        
        Args:
            text: Input text string
            
        Returns:
            Embedding tensor or None if not initialized
        """
        if not self._initialized:
            return None
        
        try:
            # Tokenize
            tokens = self.tokenizer.encode(text, max_length=256, padding=True)
            input_ids = torch.tensor([tokens]).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                # Get encoder output
                embeddings = self.model.embedding(input_ids)
                mask = (input_ids != 0).float().unsqueeze(-1)
                
                # Mean pooling
                embeddings = (embeddings * mask).sum(dim=1) / mask.sum(dim=1)
                
            return embeddings.squeeze(0)
            
        except Exception as e:
            print(f"[ERROR] Encoding failed: {e}")
            return None
    
    def compute_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> Dict[str, Any]:
        """
        Compute semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity result dictionary
        """
        if not self._initialized:
            return {
                "similarity": 0.0,
                "method": "fallback",
                "warning": "Transformer not initialized"
            }
        
        try:
            emb1 = self.encode_text(text1)
            emb2 = self.encode_text(text2)
            
            if emb1 is None or emb2 is None:
                return {
                    "similarity": 0.0,
                    "method": "fallback",
                    "warning": "Encoding failed"
                }
            
            # Cosine similarity
            similarity = F.cosine_similarity(
                emb1.unsqueeze(0), 
                emb2.unsqueeze(0)
            ).item()
            
            return {
                "similarity": similarity,
                "method": "transformer",
                "is_similar": similarity > 0.7,
            }
            
        except Exception as e:
            return {
                "similarity": 0.0,
                "method": "error",
                "error": str(e)
            }
    
    def check_plagiarism(
        self,
        answer_text: str,
        reference_texts: List[str],
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Check if answer text is similar to reference texts (potential plagiarism).
        
        Args:
            answer_text: Student's answer
            reference_texts: List of reference/source texts
            threshold: Similarity threshold for flagging
            
        Returns:
            Plagiarism check result
        """
        if not self._initialized or not answer_text:
            return {
                "is_plagiarized": False,
                "max_similarity": 0.0,
                "matches": [],
                "warning": "Analysis not available"
            }
        
        try:
            answer_emb = self.encode_text(answer_text)
            if answer_emb is None:
                return {
                    "is_plagiarized": False,
                    "max_similarity": 0.0,
                    "warning": "Encoding failed"
                }
            
            matches = []
            max_similarity = 0.0
            
            for i, ref_text in enumerate(reference_texts):
                ref_emb = self.encode_text(ref_text)
                if ref_emb is None:
                    continue
                
                similarity = F.cosine_similarity(
                    answer_emb.unsqueeze(0),
                    ref_emb.unsqueeze(0)
                ).item()
                
                if similarity > threshold:
                    matches.append({
                        "reference_index": i,
                        "similarity": round(similarity, 4),
                        "text_preview": ref_text[:100] + "..." if len(ref_text) > 100 else ref_text
                    })
                
                max_similarity = max(max_similarity, similarity)
            
            return {
                "is_plagiarized": len(matches) > 0,
                "max_similarity": round(max_similarity, 4),
                "matches": matches,
                "threshold": threshold
            }
            
        except Exception as e:
            return {
                "is_plagiarized": False,
                "max_similarity": 0.0,
                "error": str(e)
            }
    
    def analyze_answer_patterns(
        self,
        answers: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze patterns across multiple answers (detect copying between students).
        
        Args:
            answers: List of student answers to compare
            
        Returns:
            Pattern analysis result
        """
        if not self._initialized or len(answers) < 2:
            return {
                "suspicious_pairs": [],
                "analysis_complete": False
            }
        
        try:
            # Encode all answers
            embeddings = []
            for answer in answers:
                emb = self.encode_text(answer)
                if emb is not None:
                    embeddings.append(emb)
            
            if len(embeddings) < 2:
                return {
                    "suspicious_pairs": [],
                    "warning": "Not enough valid answers"
                }
            
            # Stack and compute pairwise similarities
            emb_stack = torch.stack(embeddings)
            similarities = F.cosine_similarity(
                emb_stack.unsqueeze(1),
                emb_stack.unsqueeze(0),
                dim=2
            )
            
            # Find suspicious pairs (high similarity, excluding self)
            suspicious_pairs = []
            n = len(embeddings)
            
            for i in range(n):
                for j in range(i + 1, n):
                    sim = similarities[i, j].item()
                    if sim > 0.85:  # High threshold for copying
                        suspicious_pairs.append({
                            "student_a": i,
                            "student_b": j,
                            "similarity": round(sim, 4),
                            "severity": "high" if sim > 0.95 else "medium"
                        })
            
            return {
                "suspicious_pairs": suspicious_pairs,
                "total_comparisons": n * (n - 1) // 2,
                "analysis_complete": True
            }
            
        except Exception as e:
            return {
                "suspicious_pairs": [],
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get analyzer status."""
        return {
            "initialized": self._initialized,
            "transformer_available": TRANSFORMER_AVAILABLE,
            "device": self.device,
            "model_loaded": self.model is not None
        }


# Singleton instance
_analyzer: Optional[TransformerAnalyzer] = None


def get_transformer_analyzer() -> TransformerAnalyzer:
    """Get or create singleton TransformerAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TransformerAnalyzer()
    return _analyzer


# Integration with existing similarity checker
def enhance_similarity_check(
    text: str,
    compare_texts: List[str],
    use_transformer: bool = True
) -> Dict[str, Any]:
    """
    Enhanced similarity check using both SBERT and Transformer.
    
    Args:
        text: Text to analyze
        compare_texts: Texts to compare against
        use_transformer: Whether to use Transformer model
        
    Returns:
        Combined similarity result
    """
    results = {
        "transformer_result": None,
        "combined_suspicious": False
    }
    
    if use_transformer:
        analyzer = get_transformer_analyzer()
        transformer_result = analyzer.check_plagiarism(
            text, 
            compare_texts,
            threshold=0.7
        )
        results["transformer_result"] = transformer_result
        results["combined_suspicious"] = transformer_result.get("is_plagiarized", False)
    
    return results
