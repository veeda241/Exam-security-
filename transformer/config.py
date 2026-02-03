"""
Transformer Configuration
All hyperparameters and model settings
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TransformerConfig:
    """Configuration for Transformer model"""
    
    # Model Architecture
    vocab_size: int = 32000          # Vocabulary size
    d_model: int = 512               # Embedding dimension
    n_heads: int = 8                 # Number of attention heads
    n_encoder_layers: int = 6        # Number of encoder layers
    n_decoder_layers: int = 6        # Number of decoder layers
    d_ff: int = 2048                 # Feedforward dimension
    max_seq_len: int = 512           # Maximum sequence length
    
    # Regularization
    dropout: float = 0.1             # Dropout rate
    attention_dropout: float = 0.1   # Attention dropout
    
    # Training
    batch_size: int = 32
    learning_rate: float = 1e-4
    warmup_steps: int = 4000
    max_epochs: int = 100
    gradient_clip: float = 1.0
    
    # Label smoothing
    label_smoothing: float = 0.1
    
    # Paths
    data_path: str = "./data"
    model_path: str = "./checkpoints"
    log_path: str = "./logs"
    
    # Device
    device: str = "cuda"  # or "cpu"
    
    # Special tokens
    pad_token_id: int = 0
    bos_token_id: int = 1
    eos_token_id: int = 2
    unk_token_id: int = 3


@dataclass
class SmallTransformerConfig(TransformerConfig):
    """Smaller config for testing/learning"""
    d_model: int = 256
    n_heads: int = 4
    n_encoder_layers: int = 3
    n_decoder_layers: int = 3
    d_ff: int = 1024
    max_seq_len: int = 128
    batch_size: int = 16


@dataclass  
class TinyTransformerConfig(TransformerConfig):
    """Tiny config for quick experiments"""
    vocab_size: int = 10000
    d_model: int = 128
    n_heads: int = 4
    n_encoder_layers: int = 2
    n_decoder_layers: int = 2
    d_ff: int = 512
    max_seq_len: int = 64
    batch_size: int = 8
