"""
ExamGuard Pro - Transformer-based Analysis Service
Uses custom Transformer model for advanced text analysis
"""

import sys
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

# Transformer imports - done dynamically to avoid path conflicts
TRANSFORMER_AVAILABLE = False
Transformer = None
SimpleTokenizer = None

def _load_transformer_modules():
    """Load transformer modules dynamically to avoid import conflicts."""
    global TRANSFORMER_AVAILABLE, Transformer, SimpleTokenizer
    
    try:
        # Add transformer module to path temporarily
        transformer_path = Path(__file__).parent.parent.parent / "transformer"
        if str(transformer_path) not in sys.path:
            sys.path.insert(0, str(transformer_path))
        
        from model.transformer import Transformer as Trans
        from data.tokenizer import SimpleTokenizer as STok
        
        Transformer = Trans
        SimpleTokenizer = STok
        TRANSFORMER_AVAILABLE = True
        
        # Remove from path to avoid conflicts
        if str(transformer_path) in sys.path:
            sys.path.remove(str(transformer_path))
            
    except ImportError as e:
        print(f"[WARN] Transformer module not available: {e}")
        TRANSFORMER_AVAILABLE = False


class SimilarityEncoder(nn.Module):
    """Wrapper that uses Transformer encoder for text similarity."""
    
    def __init__(self, transformer, d_model: int = 256, pooling: str = 'mean'):
        super().__init__()
        self.transformer = transformer
        self.pooling = pooling
        self.d_model = d_model
        
        # Projection head for better similarity learning
        self.projection = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model // 2),
        )
    
    def encode(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Encode text to embedding vector."""
        # Get encoder output
        encoder_output = self.transformer.encode(input_ids)  # [batch, seq, dim]
        
        # Create mask for pooling
        mask = (input_ids != self.transformer.pad_token).float()
        
        # Mean pooling (excluding padding)
        mask_expanded = mask.unsqueeze(-1).expand(encoder_output.size())
        sum_embeddings = (encoder_output * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        pooled = sum_embeddings / sum_mask
        
        # Project
        return self.projection(pooled)
    
    def forward(self, text1_ids: torch.Tensor, text2_ids: torch.Tensor):
        """Encode both texts and return embeddings."""
        emb1 = self.encode(text1_ids)
        emb2 = self.encode(text2_ids)
        return emb1, emb2


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
        self.max_length = 128
        
        # Load transformer modules dynamically
        _load_transformer_modules()
        
        if TRANSFORMER_AVAILABLE:
            self._initialize_model(model_path)
    
    def _initialize_model(self, model_path: Optional[str] = None):
        """Initialize the Transformer model."""
        try:
            # Default to trained similarity model
            if model_path is None:
                model_path = str(Path(__file__).parent.parent.parent / 
                               "transformer" / "checkpoints" / "similarity")
            
            checkpoint_file = Path(model_path) / "best_model.pt"
            tokenizer_file = Path(model_path) / "tokenizer.json"
            
            # Load tokenizer
            self.tokenizer = SimpleTokenizer(vocab_size=10000, min_freq=1)
            
            if tokenizer_file.exists():
                self.tokenizer.load(str(tokenizer_file))
                print(f"[INFO] Loaded tokenizer from {tokenizer_file}")
            else:
                # Build basic vocabulary as fallback
                sample_texts = [
                    "the a an is are was were be been being",
                    "student exam test answer question",
                    "copy paste switch tab window",
                    "photosynthesis mitochondria energy cells",
                ]
                self.tokenizer.build_vocab(sample_texts)
                print("[INFO] Using basic tokenizer vocabulary")
            
            # Load or create model
            if checkpoint_file.exists():
                checkpoint = torch.load(checkpoint_file, map_location=self.device)
                config = checkpoint['config']
                
                # Create Transformer with saved config
                transformer = Transformer(
                    src_vocab_size=config['vocab_size'],
                    tgt_vocab_size=config['vocab_size'],
                    d_model=config['d_model'],
                    n_heads=config['n_heads'],
                    n_encoder_layers=config['n_layers'],
                    n_decoder_layers=config['n_layers'],
                    d_ff=config['d_ff'],
                    max_seq_len=self.max_length,
                    dropout=0.0,  # No dropout for inference
                    pad_token=self.tokenizer.pad_token_id
                )
                
                # Create similarity encoder
                self.model = SimilarityEncoder(
                    transformer, 
                    d_model=config['d_model'],
                    pooling='mean'
                )
                
                # Load trained weights
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model = self.model.to(self.device)
                self.model.eval()
                
                print(f"[INFO] Loaded trained Transformer from {checkpoint_file}")
                print(f"[INFO] Model config: d_model={config['d_model']}, "
                      f"layers={config['n_layers']}, vocab={config['vocab_size']}")
            else:
                # Create untrained model for basic encoding
                print("[INFO] No trained model found, using untrained encoder")
                transformer = Transformer(
                    src_vocab_size=len(self.tokenizer),
                    tgt_vocab_size=len(self.tokenizer),
                    d_model=256,
                    n_heads=4,
                    n_encoder_layers=4,
                    n_decoder_layers=4,
                    d_ff=512,
                    max_seq_len=self.max_length,
                    dropout=0.0,
                    pad_token=self.tokenizer.pad_token_id
                )
                
                self.model = SimilarityEncoder(transformer, d_model=256, pooling='mean')
                self.model = self.model.to(self.device)
                self.model.eval()
            
            self._initialized = True
            print(f"[INFO] Transformer Analyzer initialized on {self.device}")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize Transformer: {e}")
            import traceback
            traceback.print_exc()
            self._initialized = False
            
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
            tokens = self.tokenizer.encode(text)[:self.max_length]
            # Pad
            tokens = tokens + [self.tokenizer.pad_token_id] * (self.max_length - len(tokens))
            input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                embedding = self.model.encode(input_ids)
                
            return embedding.squeeze(0)
            
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
