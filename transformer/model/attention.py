"""
Attention Mechanisms
- Scaled Dot-Product Attention
- Multi-Head Attention
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple


class ScaledDotProductAttention(nn.Module):
    """
    Scaled Dot-Product Attention
    
    Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V
    
    Where:
    - Q: Queries
    - K: Keys  
    - V: Values
    - d_k: Dimension of keys (for scaling)
    
    The scaling factor sqrt(d_k) prevents the dot products from growing too large,
    which would push the softmax into regions with extremely small gradients.
    """
    
    def __init__(self, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            query: (batch, n_heads, seq_len, d_k)
            key: (batch, n_heads, seq_len, d_k)
            value: (batch, n_heads, seq_len, d_v)
            mask: Optional mask tensor
            
        Returns:
            output: Attention output (batch, n_heads, seq_len, d_v)
            attention_weights: Attention weights (batch, n_heads, seq_len, seq_len)
        """
        d_k = query.size(-1)
        
        # Step 1: Compute attention scores
        # (batch, n_heads, seq_len, d_k) @ (batch, n_heads, d_k, seq_len)
        # -> (batch, n_heads, seq_len, seq_len)
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
        
        # Step 2: Apply mask (if provided)
        if mask is not None:
            # Replace masked positions with very large negative value
            scores = scores.masked_fill(mask == 0, float('-inf'))
            
        # Step 3: Softmax to get attention weights
        attention_weights = F.softmax(scores, dim=-1)
        
        # Handle NaN from softmax when entire row is masked
        attention_weights = torch.nan_to_num(attention_weights, nan=0.0)
        
        # Step 4: Apply dropout
        attention_weights = self.dropout(attention_weights)
        
        # Step 5: Apply attention to values
        # (batch, n_heads, seq_len, seq_len) @ (batch, n_heads, seq_len, d_v)
        # -> (batch, n_heads, seq_len, d_v)
        output = torch.matmul(attention_weights, value)
        
        return output, attention_weights


class MultiHeadAttention(nn.Module):
    """
    Multi-Head Attention
    
    Instead of performing a single attention function, we linearly project
    Q, K, V h times with different learned projections, perform attention
    on each, concatenate, and project again.
    
    MultiHead(Q, K, V) = Concat(head_1, ..., head_h) * W_o
    where head_i = Attention(Q*W_q_i, K*W_k_i, V*W_v_i)
    
    This allows the model to jointly attend to information from different
    representation subspaces at different positions.
    """
    
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.1
    ):
        """
        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            dropout: Dropout rate
        """
        super().__init__()
        
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads  # Dimension per head
        
        # Linear projections for Q, K, V
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        
        # Output projection
        self.w_o = nn.Linear(d_model, d_model)
        
        # Attention mechanism
        self.attention = ScaledDotProductAttention(dropout)
        
        # For storing attention weights (useful for visualization)
        self.attention_weights = None
        
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            query: (batch, seq_len, d_model)
            key: (batch, seq_len, d_model)
            value: (batch, seq_len, d_model)
            mask: Optional mask (batch, 1, 1, seq_len) or (batch, 1, seq_len, seq_len)
            
        Returns:
            output: (batch, seq_len, d_model)
        """
        batch_size = query.size(0)
        
        # Step 1: Linear projections and reshape for multi-head
        # (batch, seq_len, d_model) -> (batch, seq_len, d_model)
        # -> (batch, seq_len, n_heads, d_k) -> (batch, n_heads, seq_len, d_k)
        
        query = self.w_q(query).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        key = self.w_k(key).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        value = self.w_v(value).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        # Step 2: Apply attention
        x, attention_weights = self.attention(query, key, value, mask)
        
        # Store attention weights for visualization
        self.attention_weights = attention_weights
        
        # Step 3: Concatenate heads
        # (batch, n_heads, seq_len, d_k) -> (batch, seq_len, n_heads, d_k)
        # -> (batch, seq_len, d_model)
        x = x.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        
        # Step 4: Final linear projection
        output = self.w_o(x)
        
        return output


class SelfAttention(MultiHeadAttention):
    """
    Self-Attention (Q = K = V from same source)
    
    Used in encoder to attend to all positions in the input sequence.
    """
    
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Input tensor (batch, seq_len, d_model)
            mask: Optional mask
            
        Returns:
            output: (batch, seq_len, d_model)
        """
        return super().forward(x, x, x, mask)


class CrossAttention(MultiHeadAttention):
    """
    Cross-Attention (Q from decoder, K and V from encoder)
    
    Used in decoder to attend to encoder outputs.
    """
    
    def forward(
        self,
        query: torch.Tensor,
        encoder_output: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            query: Decoder input (batch, tgt_len, d_model)
            encoder_output: Encoder output (batch, src_len, d_model)
            mask: Optional mask
            
        Returns:
            output: (batch, tgt_len, d_model)
        """
        return super().forward(query, encoder_output, encoder_output, mask)


# ==================== VISUALIZATION ====================

def visualize_attention(attention_weights: torch.Tensor, tokens_src: list, tokens_tgt: list):
    """
    Visualize attention weights as a heatmap.
    
    Args:
        attention_weights: (seq_len_q, seq_len_k)
        tokens_src: Source tokens
        tokens_tgt: Target tokens
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    plt.figure(figsize=(10, 10))
    sns.heatmap(
        attention_weights.cpu().numpy(),
        xticklabels=tokens_src,
        yticklabels=tokens_tgt,
        cmap='viridis',
        annot=True,
        fmt='.2f'
    )
    plt.xlabel('Key (Source)')
    plt.ylabel('Query (Target)')
    plt.title('Attention Weights')
    plt.tight_layout()
    plt.savefig('attention_weights.png')
    plt.show()


if __name__ == "__main__":
    print("Testing Scaled Dot-Product Attention...")
    attention = ScaledDotProductAttention()
    
    # Create sample inputs
    batch_size, n_heads, seq_len, d_k = 2, 8, 10, 64
    q = torch.randn(batch_size, n_heads, seq_len, d_k)
    k = torch.randn(batch_size, n_heads, seq_len, d_k)
    v = torch.randn(batch_size, n_heads, seq_len, d_k)
    
    output, weights = attention(q, k, v)
    print(f"  Q/K/V shape: {q.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Weights shape: {weights.shape}")
    
    print("\nTesting Multi-Head Attention...")
    mha = MultiHeadAttention(d_model=512, n_heads=8)
    
    x = torch.randn(2, 10, 512)  # batch=2, seq_len=10, d_model=512
    output = mha(x, x, x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    
    print("\nTesting with mask...")
    mask = torch.ones(2, 1, 1, 10)
    mask[:, :, :, 5:] = 0  # Mask last 5 positions
    output = mha(x, x, x, mask)
    print(f"  Masked output shape: {output.shape}")
    
    print("\n✅ All attention tests passed!")
