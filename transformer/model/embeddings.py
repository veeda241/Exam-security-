"""
Embeddings Module
- Token Embedding: Convert token IDs to vectors
- Positional Encoding: Add position information to embeddings
"""

import torch
import torch.nn as nn
import math


class TokenEmbedding(nn.Module):
    """
    Token Embedding Layer
    
    Converts token indices to dense vectors of dimension d_model.
    The embeddings are scaled by sqrt(d_model) as per the original paper.
    """
    
    def __init__(self, vocab_size: int, d_model: int, padding_idx: int = 0):
        """
        Args:
            vocab_size: Size of vocabulary
            d_model: Embedding dimension
            padding_idx: Index of padding token (embeddings will be zeros)
        """
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)
        self.d_model = d_model
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Token indices of shape (batch_size, seq_len)
            
        Returns:
            Embeddings of shape (batch_size, seq_len, d_model)
        """
        # Scale embeddings by sqrt(d_model)
        return self.embedding(x) * math.sqrt(self.d_model)


class PositionalEncoding(nn.Module):
    """
    Positional Encoding using sine and cosine functions.
    
    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    
    This allows the model to learn relative positions since:
    PE(pos+k) can be represented as a linear function of PE(pos)
    """
    
    def __init__(self, d_model: int, max_seq_len: int = 5000, dropout: float = 0.1):
        """
        Args:
            d_model: Embedding dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
        """
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding matrix
        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        
        # Compute the div term: 10000^(2i/d_model)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        
        # Apply sine to even indices
        pe[:, 0::2] = torch.sin(position * div_term)
        # Apply cosine to odd indices
        pe[:, 1::2] = torch.cos(position * div_term)
        
        # Add batch dimension: (1, max_seq_len, d_model)
        pe = pe.unsqueeze(0)
        
        # Register as buffer (not a parameter, but should be saved)
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input embeddings of shape (batch_size, seq_len, d_model)
            
        Returns:
            Embeddings with positional encoding added
        """
        seq_len = x.size(1)
        # Add positional encoding (broadcasting over batch dimension)
        x = x + self.pe[:, :seq_len, :]
        return self.dropout(x)


class LearnedPositionalEncoding(nn.Module):
    """
    Learned Positional Encoding (alternative to sinusoidal).
    
    The positions are learned during training rather than using fixed functions.
    Used in models like GPT and BERT.
    """
    
    def __init__(self, d_model: int, max_seq_len: int = 5000, dropout: float = 0.1):
        """
        Args:
            d_model: Embedding dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
        """
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        self.position_embedding = nn.Embedding(max_seq_len, d_model)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input embeddings of shape (batch_size, seq_len, d_model)
            
        Returns:
            Embeddings with positional encoding added
        """
        batch_size, seq_len, _ = x.shape
        positions = torch.arange(seq_len, device=x.device).unsqueeze(0).expand(batch_size, -1)
        x = x + self.position_embedding(positions)
        return self.dropout(x)


class TransformerEmbedding(nn.Module):
    """
    Combined Token + Positional Embedding layer.
    
    This is the complete embedding layer used at the input of the transformer.
    """
    
    def __init__(
        self,
        vocab_size: int,
        d_model: int,
        max_seq_len: int = 5000,
        dropout: float = 0.1,
        padding_idx: int = 0,
        learned_pos: bool = False
    ):
        """
        Args:
            vocab_size: Size of vocabulary
            d_model: Embedding dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
            padding_idx: Padding token index
            learned_pos: Use learned positional encoding instead of sinusoidal
        """
        super().__init__()
        self.token_embedding = TokenEmbedding(vocab_size, d_model, padding_idx)
        
        if learned_pos:
            self.positional_encoding = LearnedPositionalEncoding(d_model, max_seq_len, dropout)
        else:
            self.positional_encoding = PositionalEncoding(d_model, max_seq_len, dropout)
            
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Token indices of shape (batch_size, seq_len)
            
        Returns:
            Embedded tokens with positional encoding of shape (batch_size, seq_len, d_model)
        """
        token_emb = self.token_embedding(x)
        return self.positional_encoding(token_emb)


# ==================== VISUALIZATION ====================

def visualize_positional_encoding(d_model: int = 128, max_len: int = 100):
    """
    Visualize positional encoding patterns.
    
    Usage:
        visualize_positional_encoding()
    """
    import matplotlib.pyplot as plt
    
    pe = PositionalEncoding(d_model, max_len, dropout=0.0)
    encoding = pe.pe.squeeze(0).numpy()
    
    plt.figure(figsize=(15, 5))
    plt.pcolormesh(encoding, cmap='viridis')
    plt.xlabel('Embedding Dimension')
    plt.ylabel('Position')
    plt.colorbar()
    plt.title('Positional Encoding Visualization')
    plt.savefig('positional_encoding.png')
    plt.show()


if __name__ == "__main__":
    # Test embeddings
    print("Testing Token Embedding...")
    token_emb = TokenEmbedding(vocab_size=10000, d_model=512)
    x = torch.randint(0, 10000, (2, 10))  # batch=2, seq_len=10
    out = token_emb(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {out.shape}")
    
    print("\nTesting Positional Encoding...")
    pos_enc = PositionalEncoding(d_model=512, max_seq_len=100)
    x = torch.randn(2, 10, 512)
    out = pos_enc(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {out.shape}")
    
    print("\nTesting Combined Embedding...")
    embedding = TransformerEmbedding(vocab_size=10000, d_model=512)
    x = torch.randint(0, 10000, (2, 10))
    out = embedding(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {out.shape}")
    
    print("\n✅ All embedding tests passed!")
