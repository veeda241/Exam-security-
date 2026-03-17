"""
ExamGuard Pro - Transformer-based Analysis Service
Uses custom Transformer models for:
  1. URL/website risk classification
  2. Behavioral anomaly detection (event sequences)
  3. Screen content risk classification (OCR text)
"""

import sys
import os
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path

import torch  # type: ignore[import-unresolved]
import torch.nn as nn  # type: ignore[import-unresolved]
import torch.nn.functional as F  # type: ignore[import-unresolved]

if TYPE_CHECKING:
    from typing import Type

# Transformer imports - done dynamically to avoid path conflicts
TRANSFORMER_AVAILABLE = False
Transformer: Any = None
SimpleTokenizer: Any = None

def _load_transformer_modules():
    """Load transformer modules dynamically to avoid import conflicts."""
    global TRANSFORMER_AVAILABLE, Transformer, SimpleTokenizer
    
    try:
        transformer_path = Path(__file__).parent.parent.parent / "transformer"
        if str(transformer_path) not in sys.path:
            sys.path.insert(0, str(transformer_path))
        
        from model.transformer import Transformer as Trans  # type: ignore[import-unresolved]
        from data.tokenizer import SimpleTokenizer as STok  # type: ignore[import-unresolved]
        
        Transformer = Trans
        SimpleTokenizer = STok
        TRANSFORMER_AVAILABLE = True
        
        if str(transformer_path) in sys.path:
            sys.path.remove(str(transformer_path))
            
    except ImportError as e:
        print(f"[WARN] Transformer module not available: {e}")
        TRANSFORMER_AVAILABLE = False


# ============================================================================
# Model wrappers (must match training architecture exactly)
# ============================================================================

class BehavioralAnomalyDetector(nn.Module):
    """Classifies sequences of student events into risk levels."""

    def __init__(self, vocab_size: int = 22, d_model: int = 128,
                 n_heads: int = 4, n_layers: int = 3, max_seq_len: int = 80,
                 num_classes: int = 4):
        super().__init__()
        self.d_model = d_model
        self.event_embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.interval_proj = nn.Linear(1, d_model)
        self.pos_embedding = nn.Embedding(max_seq_len, d_model)
        self.combine = nn.Linear(d_model * 2, d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 2,
            dropout=0.0, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.0),
            nn.Linear(d_model, num_classes),
        )

    def forward(self, event_ids: torch.Tensor, intervals: torch.Tensor) -> torch.Tensor:
        B, S = event_ids.shape
        positions = torch.arange(S, device=event_ids.device).unsqueeze(0).expand(B, -1)
        evt_emb = self.event_embedding(event_ids) + self.pos_embedding(positions)
        int_emb = self.interval_proj(intervals)
        combined = self.combine(torch.cat([evt_emb, int_emb], dim=-1))
        pad_mask = (event_ids == 0)
        encoded = self.encoder(combined, src_key_padding_mask=pad_mask)
        mask = (~pad_mask).float().unsqueeze(-1)
        pooled = (encoded * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        return self.classifier(pooled)


class ScreenContentClassifier(nn.Module):
    """Classifies OCR/screenshot text into risk categories."""

    def __init__(self, transformer, d_model: int = 256, num_classes: int = 5):
        super().__init__()
        self.transformer = transformer
        self.pool_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.0),
        )
        self.classifier = nn.Linear(d_model, num_classes)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        encoder_output = self.transformer.encode(input_ids)
        mask = (input_ids != self.transformer.pad_token).float()
        mask_expanded = mask.unsqueeze(-1).expand(encoder_output.size())
        sum_emb = (encoder_output * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        pooled = sum_emb / sum_mask
        projected = self.pool_proj(pooled)
        return self.classifier(projected)


class URLClassifier(nn.Module):
    """Transformer encoder wrapper for URL risk classification."""

    def __init__(self, transformer, d_model: int = 256, num_classes: int = 8):
        super().__init__()
        self.transformer = transformer
        self.pool_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.0),  # No dropout at inference
        )
        self.classifier = nn.Linear(d_model, num_classes)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        encoder_output = self.transformer.encode(input_ids)
        mask = (input_ids != self.transformer.pad_token).float()
        mask_expanded = mask.unsqueeze(-1).expand(encoder_output.size())
        sum_emb = (encoder_output * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        pooled = sum_emb / sum_mask
        projected = self.pool_proj(pooled)
        return self.classifier(projected)


# ============================================================================
# Risk score mapping per category
# ============================================================================

URL_CLASS_NAMES = [
    "exam_platform", "educational", "search_engine", "code_hosting",
    "social_media", "entertainment", "ai_tool", "cheating",
]

URL_CLASS_RISK = {
    "exam_platform": 0.0,
    "educational": 0.10,
    "search_engine": 0.15,
    "code_hosting": 0.35,
    "social_media": 0.45,
    "entertainment": 0.60,
    "ai_tool": 0.90,
    "cheating": 0.95,
}

SCREEN_CLASS_NAMES = ["exam_safe", "low_risk", "medium_risk", "high_risk", "critical_risk"]
SCREEN_CLASS_RISK = {
    "exam_safe": 0.0,
    "low_risk": 0.15,
    "medium_risk": 0.45,
    "high_risk": 0.70,
    "critical_risk": 0.95,
}

BEHAVIOR_CLASS_NAMES = ["normal", "mild", "high", "critical"]
BEHAVIOR_CLASS_RISK = {
    "normal": 0.0,
    "mild": 0.3,
    "high": 0.7,
    "critical": 1.0,
}


class TransformerAnalyzer:
    """
    Transformer-based analysis for ExamGuard Pro.
    
    Loads three models:
    - URL classifier            (website risk scoring)
    - Behavioral anomaly detector (event sequence risk)
    - Screen content classifier  (OCR text risk)
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.url_model: Any = None
        self.url_tokenizer: Any = None
        self.behavior_model: Any = None
        self.screen_model: Any = None
        self.screen_tokenizer: Any = None
        self._url_initialized = False
        self._behavior_initialized = False
        self._screen_initialized = False
        self._event_to_id: Dict[str, int] = {}
        
        _load_transformer_modules()
        
        if TRANSFORMER_AVAILABLE:
            self._initialize_url_classifier()
            self._initialize_behavioral()
            self._initialize_screen_content()
    
    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _load_model(self, checkpoint_dir: Path, model_cls, max_seq_len: int, **cls_kwargs):
        """Generic loader for a checkpoint + tokenizer pair."""
        checkpoint_file = checkpoint_dir / "best_model.pt"
        tokenizer_file = checkpoint_dir / "tokenizer.json"

        if not checkpoint_file.exists():
            return None, None

        tokenizer = SimpleTokenizer(vocab_size=10000, min_freq=1)
        if tokenizer_file.exists():
            tokenizer = SimpleTokenizer.load(str(tokenizer_file))
        else:
            tokenizer.build_vocab(["the a is exam test"])

        checkpoint = torch.load(checkpoint_file, map_location=self.device, weights_only=False)
        config = checkpoint["config"]

        transformer = Transformer(
            src_vocab_size=config["vocab_size"],
            tgt_vocab_size=config["vocab_size"],
            d_model=config["d_model"],
            n_heads=config["n_heads"],
            n_encoder_layers=config["n_layers"],
            n_decoder_layers=config["n_layers"],
            d_ff=config["d_ff"],
            max_seq_len=max_seq_len,
            dropout=0.0,
            pad_token=tokenizer.pad_token_id,
        )

        model = model_cls(transformer, d_model=config["d_model"], **cls_kwargs)
        model.load_state_dict(checkpoint["model_state_dict"])
        model = model.to(self.device)
        model.eval()
        return model, tokenizer

    def _initialize_behavioral(self):
        """Load the behavioral anomaly detection model."""
        try:
            behavior_path = (Path(__file__).parent.parent.parent /
                             "transformer" / "checkpoints" / "behavioral")
            checkpoint_file = behavior_path / "best_model.pt"

            if not checkpoint_file.exists():
                print("[INFO] Behavioral model checkpoint not found")
                return

            checkpoint = torch.load(checkpoint_file, map_location=self.device, weights_only=False)
            config = checkpoint["config"]

            model = BehavioralAnomalyDetector(
                vocab_size=config["event_vocab_size"],
                d_model=config["d_model"],
                n_heads=config["n_heads"],
                n_layers=config["n_layers"],
                max_seq_len=config["max_seq_len"],
                num_classes=config["num_classes"],
            )
            model.load_state_dict(checkpoint["model_state_dict"])
            model = model.to(self.device)
            model.eval()

            self.behavior_model = model
            self._event_to_id = config.get("event_to_id", {})
            self._behavior_initialized = True
            print(f"[INFO] Behavioral model loaded from {behavior_path}")

        except Exception as e:
            print(f"[WARN] Behavioral model init failed: {e}")
            self._behavior_initialized = False

    def _initialize_screen_content(self):
        """Load the screen content risk classifier."""
        try:
            screen_path = (Path(__file__).parent.parent.parent /
                           "transformer" / "checkpoints" / "screen_content")

            model, tokenizer = self._load_model(
                screen_path, ScreenContentClassifier, max_seq_len=64,
                num_classes=len(SCREEN_CLASS_NAMES),
            )

            if model is not None:
                self.screen_model = model
                self.screen_tokenizer = tokenizer
                self._screen_initialized = True
                print(f"[INFO] Screen content classifier loaded from {screen_path}")
            else:
                print("[INFO] Screen content classifier checkpoint not found")

        except Exception as e:
            print(f"[WARN] Screen content classifier init failed: {e}")
            self._screen_initialized = False

    def _initialize_url_classifier(self):
        """Load the URL risk classifier model."""
        try:
            url_path = Path(__file__).parent.parent.parent / "transformer" / "checkpoints" / "url_classifier"

            model, tokenizer = self._load_model(
                url_path, URLClassifier, max_seq_len=64,
                num_classes=len(URL_CLASS_NAMES),
            )

            if model is not None:
                self.url_model = model
                self.url_tokenizer = tokenizer
                self._url_initialized = True
                print(f"[INFO] URL classifier loaded from {url_path}")
            else:
                print("[INFO] URL classifier checkpoint not found — using rule-based fallback")
                self._url_initialized = False

        except Exception as e:
            print(f"[WARN] URL classifier init failed: {e}")
            self._url_initialized = False

    # ------------------------------------------------------------------
    # URL Classification
    # ------------------------------------------------------------------

    def classify_url(self, url: str) -> Dict[str, Any]:
        """
        Classify a URL into a risk category using the transformer.
        Falls back to rule-based classification if model is unavailable.
        """
        if not self._url_initialized:
            # Rule-based fallback (import from config)
            try:
                from config import classify_url as rule_classify
                result = rule_classify(url)
                if result:
                    return {
                        "url": url,
                        "category": result["category"].lower(),
                        "risk_score": URL_CLASS_RISK.get(result["category"].lower(), 0.5),
                        "confidence": 1.0,
                        "method": "rule_based",
                    }
            except Exception:
                pass
            return {
                "url": url,
                "category": "unknown",
                "risk_score": 0.2,
                "confidence": 0.0,
                "method": "fallback",
            }

        try:
            tokens = self.url_tokenizer.encode(url)[:64]
            tokens += [self.url_tokenizer.pad_token_id] * (64 - len(tokens))
            input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)

            with torch.no_grad():
                logits = self.url_model(input_ids)
                probs = F.softmax(logits, dim=1).squeeze(0)
                pred_idx = probs.argmax().item()
                confidence = probs[pred_idx].item()

            category = URL_CLASS_NAMES[pred_idx]
            risk_score = URL_CLASS_RISK[category]

            return {
                "url": url,
                "category": category,
                "risk_score": risk_score,
                "confidence": round(confidence, 4),
                "method": "transformer",
                "all_scores": {
                    URL_CLASS_NAMES[i]: round(probs[i].item(), 4)
                    for i in range(len(URL_CLASS_NAMES))
                },
            }

        except Exception as e:
            return {
                "url": url,
                "category": "unknown",
                "risk_score": 0.2,
                "confidence": 0.0,
                "method": "error",
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Behavioral Anomaly Detection
    # ------------------------------------------------------------------

    def predict_behavior_risk(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict risk level from a sequence of student events.
        
        Args:
            events: List of {"type": "TAB_SWITCH", "timestamp": ..., ...}
        
        Returns:
            Dict with risk_level, risk_score, confidence, method
        """
        if not self._behavior_initialized or not events:
            return {
                "risk_level": "unknown",
                "risk_score": 0.0,
                "confidence": 0.0,
                "method": "unavailable",
            }

        try:
            max_len = 80
            event_ids = []
            intervals = []

            prev_ts = None
            for e in events[:max_len]:
                etype = e.get("type", e.get("event", "FOCUS"))
                eid = self._event_to_id.get(etype, 1)  # UNK
                event_ids.append(eid)

                ts = e.get("timestamp", 0)
                interval = min((ts - prev_ts) / 10000.0, 1.0) if prev_ts and ts else 0.2
                intervals.append(interval)
                prev_ts = ts

            # Pad
            pad_len = max_len - len(event_ids)
            event_ids += [0] * pad_len
            intervals += [0.0] * pad_len

            eids_t = torch.tensor([event_ids], dtype=torch.long).to(self.device)
            ints_t = torch.tensor([intervals], dtype=torch.float).unsqueeze(-1).to(self.device)

            with torch.no_grad():
                logits = self.behavior_model(eids_t, ints_t)
                probs = F.softmax(logits, dim=1).squeeze(0)
                pred_idx = probs.argmax().item()
                confidence = probs[pred_idx].item()

            risk_level = BEHAVIOR_CLASS_NAMES[pred_idx]
            risk_score = BEHAVIOR_CLASS_RISK[risk_level]

            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "confidence": round(confidence, 4),
                "method": "transformer",
                "all_scores": {
                    BEHAVIOR_CLASS_NAMES[i]: round(probs[i].item(), 4)
                    for i in range(len(BEHAVIOR_CLASS_NAMES))
                },
            }
        except Exception as e:
            return {
                "risk_level": "unknown",
                "risk_score": 0.0,
                "confidence": 0.0,
                "method": "error",
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Screen Content Classification
    # ------------------------------------------------------------------

    def classify_screen_content(self, text: str) -> Dict[str, Any]:
        """
        Classify OCR/screenshot text into a risk category.
        
        Args:
            text: Text extracted from screenshot or page title
        
        Returns:
            Dict with category, risk_score, confidence, method
        """
        if not self._screen_initialized or not text:
            return {
                "category": "unknown",
                "risk_score": 0.0,
                "confidence": 0.0,
                "method": "unavailable",
            }

        try:
            tokens = self.screen_tokenizer.encode(text)[:64]
            tokens += [self.screen_tokenizer.pad_token_id] * (64 - len(tokens))
            input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)

            with torch.no_grad():
                logits = self.screen_model(input_ids)
                probs = F.softmax(logits, dim=1).squeeze(0)
                pred_idx = probs.argmax().item()
                confidence = probs[pred_idx].item()

            category = SCREEN_CLASS_NAMES[pred_idx]
            risk_score = SCREEN_CLASS_RISK[category]

            return {
                "category": category,
                "risk_score": risk_score,
                "confidence": round(confidence, 4),
                "method": "transformer",
                "all_scores": {
                    SCREEN_CLASS_NAMES[i]: round(probs[i].item(), 4)
                    for i in range(len(SCREEN_CLASS_NAMES))
                },
            }
        except Exception as e:
            return {
                "category": "unknown",
                "risk_score": 0.0,
                "confidence": 0.0,
                "method": "error",
                "error": str(e),
            }

    def get_status(self) -> Dict[str, Any]:
        """Get analyzer status."""
        return {
            "url_classifier_loaded": self._url_initialized,
            "behavior_model_loaded": self._behavior_initialized,
            "screen_model_loaded": self._screen_initialized,
            "transformer_available": TRANSFORMER_AVAILABLE,
            "device": self.device,
        }


# Singleton
_analyzer: Optional[TransformerAnalyzer] = None


def get_transformer_analyzer() -> TransformerAnalyzer:
    """Get or create singleton TransformerAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TransformerAnalyzer()
    return _analyzer



