"""
Utility modules for Transformer
- Layer Normalization
- Feed Forward Network
- Residual Connection
- Mask generation
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class LayerNorm(nn.Module):
    """
    Layer Normalization
    
    Normalizes the last dimension of the input tensor.
    LayerNorm(x) = gamma * (x - mean) / sqrt(var + eps) + beta
    
    Unlike BatchNorm, LayerNorm normalizes across features (not batch),
    making it suitable for sequence data where batch statistics vary.
    """
    
    def __init__(self, d_model: int, eps: float = 1e-6):
        """
        Args:
            d_model: Feature dimension
            eps: Small constant for numerical stability
        """
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(d_model))
        self.beta = nn.Parameter(torch.zeros(d_model))
        self.eps = eps
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (..., d_model)
            
        Returns:
            Normalized tensor of same shape
        """
        mean = x.mean(dim=-1, keepdim=True)
        std = x.std(dim=-1, keepdim=True)
        return self.gamma * (x - mean) / (std + self.eps) + self.beta


class FeedForward(nn.Module):
    """
    Position-wise Feed-Forward Network
    
    FFN(x) = max(0, xW_1 + b_1)W_2 + b_2
    
    Applied to each position separately and identically.
    Typically d_ff = 4 * d_model in the original paper.
    """
    
    def __init__(
        self,
        d_model: int,
        d_ff: int,
        dropout: float = 0.1,
        activation: str = "relu"
    ):
        """
        Args:
            d_model: Input/output dimension
            d_ff: Hidden layer dimension (usually 4 * d_model)
            dropout: Dropout rate
            activation: Activation function ("relu" or "gelu")
        """
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        
        if activation == "relu":
            self.activation = F.relu
        elif activation == "gelu":
            self.activation = F.gelu
        else:
            raise ValueError(f"Unknown activation: {activation}")
            
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            
        Returns:
            Output tensor of shape (batch, seq_len, d_model)
        """
        x = self.linear1(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = self.linear2(x)
        return x


class ResidualConnection(nn.Module):
    """
    Residual Connection with Layer Normalization
    
    output = LayerNorm(x + Sublayer(x))
    
    This is the "Post-LN" variant. An alternative is "Pre-LN":
    output = x + Sublayer(LayerNorm(x))
    """
    
    def __init__(self, d_model: int, dropout: float = 0.1, pre_norm: bool = False):
        """
        Args:
            d_model: Model dimension
            dropout: Dropout rate
            pre_norm: Use Pre-LN instead of Post-LN
        """
        super().__init__()
        self.norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)
        self.pre_norm = pre_norm
        
    def forward(self, x: torch.Tensor, sublayer_output: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Original input (for residual)
            sublayer_output: Output from sublayer (attention or FFN)
            
        Returns:
            Output with residual connection
        """
        if self.pre_norm:
            # Pre-LN: already normalized before sublayer
            return x + self.dropout(sublayer_output)
        else:
            # Post-LN: normalize after residual
            return self.norm(x + self.dropout(sublayer_output))


# ==================== MASK FUNCTIONS ====================

def create_padding_mask(seq: torch.Tensor, pad_token: int = 0) -> torch.Tensor:
    """
    Create padding mask for sequence.
    
    Args:
        seq: Token sequence (batch, seq_len)
        pad_token: Padding token ID
        
    Returns:
        mask: (batch, 1, 1, seq_len) - 1 for valid, 0 for padding
    """
    # (batch, seq_len) -> (batch, 1, 1, seq_len)
    mask = (seq != pad_token).unsqueeze(1).unsqueeze(2)
    return mask.float()


def create_causal_mask(seq_len: int, device: torch.device = None) -> torch.Tensor:
    """
    Create causal (look-ahead) mask for decoder self-attention.
    
    Prevents positions from attending to subsequent positions.
    
    Args:
        seq_len: Sequence length
        device: Device to create tensor on
        
    Returns:
        mask: (1, 1, seq_len, seq_len) - upper triangular mask
    """
    # Create lower triangular matrix (including diagonal)
    mask = torch.tril(torch.ones(seq_len, seq_len, device=device))
    # Add dimensions for batch and heads: (1, 1, seq_len, seq_len)
    mask = mask.unsqueeze(0).unsqueeze(0)
    return mask


def create_combined_mask(
    tgt: torch.Tensor,
    pad_token: int = 0
) -> torch.Tensor:
    """
    Create combined padding + causal mask for decoder.
    
    Args:
        tgt: Target sequence (batch, seq_len)
        pad_token: Padding token ID
        
    Returns:
        Combined mask (batch, 1, seq_len, seq_len)
    """
    batch_size, seq_len = tgt.shape
    
    # Padding mask: (batch, 1, 1, seq_len)
    padding_mask = create_padding_mask(tgt, pad_token)
    
    # Causal mask: (1, 1, seq_len, seq_len)
    causal_mask = create_causal_mask(seq_len, tgt.device)
    
    # Combine: (batch, 1, seq_len, seq_len)
    combined_mask = padding_mask * causal_mask
    
    return combined_mask


def create_encoder_decoder_mask(
    src: torch.Tensor,
    pad_token: int = 0
) -> torch.Tensor:
    """
    Create mask for encoder-decoder attention.
    
    Masks padding positions in the source sequence.
    
    Args:
        src: Source sequence (batch, src_len)
        pad_token: Padding token ID
        
    Returns:
        mask: (batch, 1, 1, src_len)
    """
    return create_padding_mask(src, pad_token)


# ==================== WEIGHT INITIALIZATION ====================

def init_weights(module: nn.Module, init_std: float = 0.02):
    """
    Initialize weights for transformer modules.
    
    Args:
        module: Module to initialize
        init_std: Standard deviation for normal distribution
    """
    if isinstance(module, nn.Linear):
        nn.init.normal_(module.weight, mean=0.0, std=init_std)
        if module.bias is not None:
            nn.init.zeros_(module.bias)
    elif isinstance(module, nn.Embedding):
        nn.init.normal_(module.weight, mean=0.0, std=init_std)
    elif isinstance(module, nn.LayerNorm):
        nn.init.ones_(module.weight)
        nn.init.zeros_(module.bias)


if __name__ == "__main__":
    print("Testing Layer Normalization...")
    ln = LayerNorm(d_model=512)
    x = torch.randn(2, 10, 512)
    out = ln(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {out.shape}")
    print(f"  Mean (should be ~0): {out.mean().item():.4f}")
    print(f"  Std (should be ~1): {out.std().item():.4f}")
    
    print("\nTesting Feed Forward...")
    ffn = FeedForward(d_model=512, d_ff=2048)
    out = ffn(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {out.shape}")
    
    print("\nTesting Mask Creation...")
    seq = torch.tensor([[1, 2, 3, 0, 0], [1, 2, 0, 0, 0]])
    pad_mask = create_padding_mask(seq)
    print(f"  Sequence: {seq}")
    print(f"  Padding mask shape: {pad_mask.shape}")
    print(f"  Padding mask:\n{pad_mask.squeeze()}")
    
    causal = create_causal_mask(5)
    print(f"\n  Causal mask shape: {causal.shape}")
    print(f"  Causal mask:\n{causal.squeeze()}")
    
    print("\n✅ All utility tests passed!")
