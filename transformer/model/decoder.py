"""
Decoder Module
- Decoder Block (Masked Self-Attention + Cross-Attention + Feed Forward)
- Decoder Stack (N decoder blocks)
"""

import torch
import torch.nn as nn
from typing import Optional

from model.attention import MultiHeadAttention
from model.utils import FeedForward


class DecoderBlock(nn.Module):
    """
    Single Decoder Block
    
    Each block consists of:
    1. Masked Multi-Head Self-Attention with residual connection
    2. Multi-Head Cross-Attention (to encoder output) with residual connection
    3. Position-wise Feed-Forward Network with residual connection
    
    Architecture:
        x -> [Masked Self-Attn] -> [Add & Norm] 
          -> [Cross-Attn] -> [Add & Norm]
          -> [FFN] -> [Add & Norm] -> output
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
        
        # Masked Self-Attention sublayer
        self.self_attention = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        
        # Cross-Attention sublayer (attends to encoder output)
        self.cross_attention = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)
        
        # Feed-Forward sublayer
        self.feed_forward = FeedForward(d_model, d_ff, dropout, activation)
        self.norm3 = nn.LayerNorm(d_model)
        self.dropout3 = nn.Dropout(dropout)
        
    def forward(
        self,
        x: torch.Tensor,
        encoder_output: torch.Tensor,
        self_attn_mask: Optional[torch.Tensor] = None,
        cross_attn_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Decoder input (batch, tgt_len, d_model)
            encoder_output: Encoder output (batch, src_len, d_model)
            self_attn_mask: Causal mask for self-attention (batch, 1, tgt_len, tgt_len)
            cross_attn_mask: Padding mask for cross-attention (batch, 1, 1, src_len)
            
        Returns:
            Output tensor (batch, tgt_len, d_model)
        """
        if self.pre_norm:
            # Pre-LN variant
            # Masked Self-Attention
            normalized = self.norm1(x)
            self_attn_out = self.self_attention(normalized, normalized, normalized, self_attn_mask)
            x = x + self.dropout1(self_attn_out)
            
            # Cross-Attention
            normalized = self.norm2(x)
            cross_attn_out = self.cross_attention(normalized, encoder_output, encoder_output, cross_attn_mask)
            x = x + self.dropout2(cross_attn_out)
            
            # Feed-Forward
            normalized = self.norm3(x)
            ff_out = self.feed_forward(normalized)
            x = x + self.dropout3(ff_out)
        else:
            # Post-LN variant (original paper)
            # Masked Self-Attention
            self_attn_out = self.self_attention(x, x, x, self_attn_mask)
            x = self.norm1(x + self.dropout1(self_attn_out))
            
            # Cross-Attention
            cross_attn_out = self.cross_attention(x, encoder_output, encoder_output, cross_attn_mask)
            x = self.norm2(x + self.dropout2(cross_attn_out))
            
            # Feed-Forward
            ff_out = self.feed_forward(x)
            x = self.norm3(x + self.dropout3(ff_out))
            
        return x


class Decoder(nn.Module):
    """
    Transformer Decoder
    
    Stack of N identical decoder blocks.
    
    The decoder generates the output sequence one token at a time,
    attending to both its previous outputs and the encoder representations.
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
            n_layers: Number of decoder blocks
            d_model: Model dimension
            n_heads: Number of attention heads
            d_ff: Feed-forward hidden dimension
            dropout: Dropout rate
            activation: Activation function for FFN
            pre_norm: Use Pre-LN instead of Post-LN
        """
        super().__init__()
        
        self.layers = nn.ModuleList([
            DecoderBlock(d_model, n_heads, d_ff, dropout, activation, pre_norm)
            for _ in range(n_layers)
        ])
        
        # Final layer norm (used with Pre-LN)
        self.norm = nn.LayerNorm(d_model) if pre_norm else nn.Identity()
        
    def forward(
        self,
        x: torch.Tensor,
        encoder_output: torch.Tensor,
        self_attn_mask: Optional[torch.Tensor] = None,
        cross_attn_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Target embeddings (batch, tgt_len, d_model)
            encoder_output: Encoder output (batch, src_len, d_model)
            self_attn_mask: Causal mask (batch, 1, tgt_len, tgt_len)
            cross_attn_mask: Source padding mask (batch, 1, 1, src_len)
            
        Returns:
            Decoder output (batch, tgt_len, d_model)
        """
        for layer in self.layers:
            x = layer(x, encoder_output, self_attn_mask, cross_attn_mask)
            
        # Apply final norm if using Pre-LN
        x = self.norm(x)
        
        return x


if __name__ == "__main__":
    print("Testing Decoder Block...")
    decoder_block = DecoderBlock(
        d_model=512,
        n_heads=8,
        d_ff=2048,
        dropout=0.1
    )
    
    # Decoder input
    x = torch.randn(2, 8, 512)  # batch=2, tgt_len=8
    # Encoder output
    encoder_out = torch.randn(2, 10, 512)  # batch=2, src_len=10
    
    output = decoder_block(x, encoder_out)
    print(f"  Decoder input shape: {x.shape}")
    print(f"  Encoder output shape: {encoder_out.shape}")
    print(f"  Output shape: {output.shape}")
    
    # Test with masks
    from model.utils import create_causal_mask, create_padding_mask
    
    # Causal mask for self-attention
    causal_mask = create_causal_mask(8, x.device)
    # Padding mask for cross-attention
    src = torch.tensor([[1, 2, 3, 4, 5, 0, 0, 0, 0, 0], 
                        [1, 2, 3, 4, 5, 6, 7, 0, 0, 0]])
    cross_mask = create_padding_mask(src)
    
    output = decoder_block(x, encoder_out, causal_mask, cross_mask)
    print(f"  Masked output shape: {output.shape}")
    
    print("\nTesting Decoder Stack...")
    decoder = Decoder(
        n_layers=6,
        d_model=512,
        n_heads=8,
        d_ff=2048,
        dropout=0.1
    )
    
    output = decoder(x, encoder_out)
    print(f"  Output shape: {output.shape}")
    print(f"\n  Total parameters: {sum(p.numel() for p in decoder.parameters()):,}")
    
    print("\n✅ All decoder tests passed!")
