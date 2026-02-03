"""
Encoder Module
- Encoder Block (Self-Attention + Feed Forward)
- Encoder Stack (N encoder blocks)
"""

import torch
import torch.nn as nn
from typing import Optional

from model.attention import MultiHeadAttention
from model.utils import FeedForward, ResidualConnection


class EncoderBlock(nn.Module):
    """
    Single Encoder Block
    
    Each block consists of:
    1. Multi-Head Self-Attention with residual connection
    2. Position-wise Feed-Forward Network with residual connection
    
    Architecture:
        x -> [Self-Attn] -> [Add & Norm] -> [FFN] -> [Add & Norm] -> output
    """
    
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
        activation: str = "relu",
        pre_norm: bool = False
    ):
        """
        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            d_ff: Feed-forward hidden dimension
            dropout: Dropout rate
            activation: Activation function for FFN
            pre_norm: Use Pre-LN instead of Post-LN
        """
        super().__init__()
        
        self.pre_norm = pre_norm
        
        # Self-Attention sublayer
        self.self_attention = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        
        # Feed-Forward sublayer
        self.feed_forward = FeedForward(d_model, d_ff, dropout, activation)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)
        
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Input tensor (batch, seq_len, d_model)
            mask: Optional padding mask (batch, 1, 1, seq_len)
            
        Returns:
            Output tensor (batch, seq_len, d_model)
        """
        if self.pre_norm:
            # Pre-LN: Normalize before sublayer
            # Self-Attention
            normalized = self.norm1(x)
            attn_out = self.self_attention(normalized, normalized, normalized, mask)
            x = x + self.dropout1(attn_out)
            
            # Feed-Forward
            normalized = self.norm2(x)
            ff_out = self.feed_forward(normalized)
            x = x + self.dropout2(ff_out)
        else:
            # Post-LN: Normalize after residual (original paper)
            # Self-Attention
            attn_out = self.self_attention(x, x, x, mask)
            x = self.norm1(x + self.dropout1(attn_out))
            
            # Feed-Forward
            ff_out = self.feed_forward(x)
            x = self.norm2(x + self.dropout2(ff_out))
            
        return x


class Encoder(nn.Module):
    """
    Transformer Encoder
    
    Stack of N identical encoder blocks.
    
    The encoder processes the input sequence and creates representations
    that contain information about which parts of the input are relevant.
    """
    
    def __init__(
        self,
        n_layers: int,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
        activation: str = "relu",
        pre_norm: bool = False
    ):
        """
        Args:
            n_layers: Number of encoder blocks
            d_model: Model dimension
            n_heads: Number of attention heads
            d_ff: Feed-forward hidden dimension
            dropout: Dropout rate
            activation: Activation function for FFN
            pre_norm: Use Pre-LN instead of Post-LN
        """
        super().__init__()
        
        self.layers = nn.ModuleList([
            EncoderBlock(d_model, n_heads, d_ff, dropout, activation, pre_norm)
            for _ in range(n_layers)
        ])
        
        # Final layer norm (used with Pre-LN)
        self.norm = nn.LayerNorm(d_model) if pre_norm else nn.Identity()
        
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Input embeddings (batch, seq_len, d_model)
            mask: Optional padding mask (batch, 1, 1, seq_len)
            
        Returns:
            Encoder output (batch, seq_len, d_model)
        """
        for layer in self.layers:
            x = layer(x, mask)
            
        # Apply final norm if using Pre-LN
        x = self.norm(x)
        
        return x


if __name__ == "__main__":
    print("Testing Encoder Block...")
    encoder_block = EncoderBlock(
        d_model=512,
        n_heads=8,
        d_ff=2048,
        dropout=0.1
    )
    
    x = torch.randn(2, 10, 512)  # batch=2, seq_len=10
    output = encoder_block(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    
    # Test with mask
    mask = torch.ones(2, 1, 1, 10)
    mask[:, :, :, 7:] = 0  # Mask last 3 positions
    output = encoder_block(x, mask)
    print(f"  Masked output shape: {output.shape}")
    
    print("\nTesting Encoder Stack...")
    encoder = Encoder(
        n_layers=6,
        d_model=512,
        n_heads=8,
        d_ff=2048,
        dropout=0.1
    )
    
    output = encoder(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    
    print(f"\n  Total parameters: {sum(p.numel() for p in encoder.parameters()):,}")
    
    print("\n✅ All encoder tests passed!")
