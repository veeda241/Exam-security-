"""
Complete Transformer Model
Combines Encoder and Decoder with embeddings and output projection.
"""

import torch
import torch.nn as nn
from typing import Optional, Dict, Any
import math

from model.embeddings import TransformerEmbedding
from model.encoder import Encoder
from model.decoder import Decoder
from model.utils import create_padding_mask, create_combined_mask, init_weights


class Transformer(nn.Module):
    """
    Transformer Model (Encoder-Decoder Architecture)
    
    As described in "Attention Is All You Need" (Vaswani et al., 2017)
    
    Architecture:
        Source -> Embedding -> Encoder -> Context
        Target -> Embedding -> Decoder (with Context) -> Linear -> Logits
    
    Used for sequence-to-sequence tasks like:
    - Machine Translation
    - Text Summarization
    - Question Answering
    """
    
    def __init__(
        self,
        src_vocab_size: int,
        tgt_vocab_size: int,
        d_model: int = 512,
        n_heads: int = 8,
        n_encoder_layers: int = 6,
        n_decoder_layers: int = 6,
        d_ff: int = 2048,
        max_seq_len: int = 512,
        dropout: float = 0.1,
        pad_token: int = 0,
        activation: str = "relu",
        pre_norm: bool = False,
        share_embeddings: bool = False,
        tie_output_weights: bool = True
    ):
        """
        Args:
            src_vocab_size: Source vocabulary size
            tgt_vocab_size: Target vocabulary size
            d_model: Model dimension
            n_heads: Number of attention heads
            n_encoder_layers: Number of encoder layers
            n_decoder_layers: Number of decoder layers
            d_ff: Feed-forward hidden dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
            pad_token: Padding token ID
            activation: Activation function ("relu" or "gelu")
            pre_norm: Use Pre-LN instead of Post-LN
            share_embeddings: Share embeddings between encoder and decoder
            tie_output_weights: Tie decoder embeddings with output projection
        """
        super().__init__()
        
        self.pad_token = pad_token
        self.d_model = d_model
        
        # Source embedding (Encoder input)
        self.src_embedding = TransformerEmbedding(
            src_vocab_size, d_model, max_seq_len, dropout, pad_token
        )
        
        # Target embedding (Decoder input)
        if share_embeddings and src_vocab_size == tgt_vocab_size:
            self.tgt_embedding = self.src_embedding
        else:
            self.tgt_embedding = TransformerEmbedding(
                tgt_vocab_size, d_model, max_seq_len, dropout, pad_token
            )
        
        # Encoder
        self.encoder = Encoder(
            n_layers=n_encoder_layers,
            d_model=d_model,
            n_heads=n_heads,
            d_ff=d_ff,
            dropout=dropout,
            activation=activation,
            pre_norm=pre_norm
        )
        
        # Decoder
        self.decoder = Decoder(
            n_layers=n_decoder_layers,
            d_model=d_model,
            n_heads=n_heads,
            d_ff=d_ff,
            dropout=dropout,
            activation=activation,
            pre_norm=pre_norm
        )
        
        # Output projection (decoder hidden -> vocabulary logits)
        self.output_projection = nn.Linear(d_model, tgt_vocab_size)
        
        # Optionally tie output weights with decoder embeddings
        if tie_output_weights:
            self.output_projection.weight = self.tgt_embedding.token_embedding.embedding.weight
            
        # Initialize weights
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        """Initialize weights following the original paper."""
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0, std=self.d_model ** -0.5)
        elif isinstance(module, nn.LayerNorm):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)
            
    def encode(
        self,
        src: torch.Tensor,
        src_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Encode source sequence.
        
        Args:
            src: Source token IDs (batch, src_len)
            src_mask: Source padding mask
            
        Returns:
            Encoder output (batch, src_len, d_model)
        """
        # Create mask if not provided
        if src_mask is None:
            src_mask = create_padding_mask(src, self.pad_token)
            
        # Embed and encode
        src_embedded = self.src_embedding(src)
        encoder_output = self.encoder(src_embedded, src_mask)
        
        return encoder_output
    
    def decode(
        self,
        tgt: torch.Tensor,
        encoder_output: torch.Tensor,
        tgt_mask: Optional[torch.Tensor] = None,
        src_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Decode target sequence.
        
        Args:
            tgt: Target token IDs (batch, tgt_len)
            encoder_output: Encoder output (batch, src_len, d_model)
            tgt_mask: Target causal mask
            src_mask: Source padding mask (for cross-attention)
            
        Returns:
            Decoder output (batch, tgt_len, d_model)
        """
        # Create mask if not provided
        if tgt_mask is None:
            tgt_mask = create_combined_mask(tgt, self.pad_token)
            
        # Embed and decode
        tgt_embedded = self.tgt_embedding(tgt)
        decoder_output = self.decoder(
            tgt_embedded, encoder_output, tgt_mask, src_mask
        )
        
        return decoder_output
        
    def forward(
        self,
        src: torch.Tensor,
        tgt: torch.Tensor,
        src_mask: Optional[torch.Tensor] = None,
        tgt_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass through the Transformer.
        
        Args:
            src: Source token IDs (batch, src_len)
            tgt: Target token IDs (batch, tgt_len)
            src_mask: Source padding mask
            tgt_mask: Target causal mask
            
        Returns:
            Logits (batch, tgt_len, tgt_vocab_size)
        """
        # Create masks if not provided
        if src_mask is None:
            src_mask = create_padding_mask(src, self.pad_token)
        if tgt_mask is None:
            tgt_mask = create_combined_mask(tgt, self.pad_token)
            
        # Encode
        encoder_output = self.encode(src, src_mask)
        
        # Decode
        decoder_output = self.decode(tgt, encoder_output, tgt_mask, src_mask)
        
        # Project to vocabulary
        logits = self.output_projection(decoder_output)
        
        return logits
    
    def generate(
        self,
        src: torch.Tensor,
        max_len: int = 100,
        start_token: int = 1,
        end_token: int = 2,
        temperature: float = 1.0,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None
    ) -> torch.Tensor:
        """
        Generate output sequence autoregressively.
        
        Args:
            src: Source token IDs (batch, src_len)
            max_len: Maximum generation length
            start_token: Start of sequence token ID
            end_token: End of sequence token ID
            temperature: Sampling temperature (1.0 = normal, <1.0 = sharper, >1.0 = smoother)
            top_k: Sample from top-k tokens (optional)
            top_p: Sample from top-p probability mass (nucleus sampling, optional)
            
        Returns:
            Generated token IDs (batch, gen_len)
        """
        self.eval()
        batch_size = src.size(0)
        device = src.device
        
        # Encode source
        src_mask = create_padding_mask(src, self.pad_token)
        encoder_output = self.encode(src, src_mask)
        
        # Initialize with start token
        generated = torch.full((batch_size, 1), start_token, dtype=torch.long, device=device)
        
        # Track which sequences have finished
        finished = torch.zeros(batch_size, dtype=torch.bool, device=device)
        
        for _ in range(max_len - 1):
            # Decode current sequence
            tgt_mask = create_combined_mask(generated, self.pad_token)
            decoder_output = self.decode(generated, encoder_output, tgt_mask, src_mask)
            
            # Get logits for last position
            logits = self.output_projection(decoder_output[:, -1, :])
            
            # Apply temperature
            logits = logits / temperature
            
            # Apply top-k filtering
            if top_k is not None:
                indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
                logits[indices_to_remove] = float('-inf')
                
            # Apply top-p (nucleus) filtering
            if top_p is not None:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                
                # Remove tokens with cumulative probability above threshold
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                logits[indices_to_remove] = float('-inf')
            
            # Sample next token
            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            
            # Add to generated sequence
            generated = torch.cat([generated, next_token], dim=1)
            
            # Check for end token
            finished = finished | (next_token.squeeze(-1) == end_token)
            if finished.all():
                break
                
        return generated
    
    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return {
            "src_vocab_size": self.src_embedding.token_embedding.embedding.num_embeddings,
            "tgt_vocab_size": self.output_projection.out_features,
            "d_model": self.d_model,
            "pad_token": self.pad_token,
        }


class TransformerEncoderOnly(nn.Module):
    """
    Transformer Encoder-Only Model
    
    Used for classification and encoding tasks like:
    - BERT-style models
    - Text Classification
    - Named Entity Recognition
    """
    
    def __init__(
        self,
        vocab_size: int,
        d_model: int = 512,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 2048,
        max_seq_len: int = 512,
        dropout: float = 0.1,
        pad_token: int = 0,
        num_classes: Optional[int] = None,
        pooling: str = "cls"
    ):
        """
        Args:
            vocab_size: Vocabulary size
            d_model: Model dimension
            n_heads: Number of attention heads
            n_layers: Number of encoder layers
            d_ff: Feed-forward hidden dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
            pad_token: Padding token ID
            num_classes: Number of output classes (for classification)
            pooling: Pooling strategy ("cls", "mean", "max")
        """
        super().__init__()
        
        self.pad_token = pad_token
        self.pooling = pooling
        
        # Embedding
        self.embedding = TransformerEmbedding(
            vocab_size, d_model, max_seq_len, dropout, pad_token
        )
        
        # Encoder
        self.encoder = Encoder(
            n_layers=n_layers,
            d_model=d_model,
            n_heads=n_heads,
            d_ff=d_ff,
            dropout=dropout
        )
        
        # Classification head (optional)
        self.classifier = None
        if num_classes is not None:
            self.classifier = nn.Linear(d_model, num_classes)
            
    def forward(
        self,
        src: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            src: Input token IDs (batch, seq_len)
            mask: Padding mask
            
        Returns:
            If classifier: logits (batch, num_classes)
            Else: encoder output (batch, seq_len, d_model)
        """
        # Create mask if not provided
        if mask is None:
            mask = create_padding_mask(src, self.pad_token)
            
        # Embed and encode
        x = self.embedding(src)
        x = self.encoder(x, mask)
        
        # Apply pooling if classifier exists
        if self.classifier is not None:
            if self.pooling == "cls":
                x = x[:, 0, :]  # Use [CLS] token (first token)
            elif self.pooling == "mean":
                # Mean pooling (excluding padding)
                mask_expanded = mask.squeeze(1).squeeze(1).unsqueeze(-1)
                x = (x * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1)
            elif self.pooling == "max":
                x = x.max(dim=1)[0]
            
            x = self.classifier(x)
            
        return x


class TransformerDecoderOnly(nn.Module):
    """
    Transformer Decoder-Only Model (GPT-style)
    
    Used for language modeling and generation tasks like:
    - GPT-style models
    - Text Generation
    - Code Generation
    """
    
    def __init__(
        self,
        vocab_size: int,
        d_model: int = 512,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 2048,
        max_seq_len: int = 512,
        dropout: float = 0.1,
        pad_token: int = 0,
        tie_weights: bool = True
    ):
        """
        Args:
            vocab_size: Vocabulary size
            d_model: Model dimension
            n_heads: Number of attention heads
            n_layers: Number of decoder layers
            d_ff: Feed-forward hidden dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
            pad_token: Padding token ID
            tie_weights: Tie embedding and output weights
        """
        super().__init__()
        
        self.pad_token = pad_token
        self.d_model = d_model
        
        # Embedding
        self.embedding = TransformerEmbedding(
            vocab_size, d_model, max_seq_len, dropout, pad_token
        )
        
        # Decoder blocks (without cross-attention)
        self.layers = nn.ModuleList([
            DecoderOnlyBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])
        
        self.norm = nn.LayerNorm(d_model)
        
        # Output projection
        self.output_projection = nn.Linear(d_model, vocab_size)
        
        if tie_weights:
            self.output_projection.weight = self.embedding.token_embedding.embedding.weight
            
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input token IDs (batch, seq_len)
            mask: Causal mask
            
        Returns:
            Logits (batch, seq_len, vocab_size)
        """
        # Create causal mask if not provided
        if mask is None:
            mask = create_combined_mask(x, self.pad_token)
            
        # Embed
        x = self.embedding(x)
        
        # Pass through decoder layers
        for layer in self.layers:
            x = layer(x, mask)
            
        x = self.norm(x)
        
        # Project to vocabulary
        logits = self.output_projection(x)
        
        return logits


class DecoderOnlyBlock(nn.Module):
    """Decoder block without cross-attention (for GPT-style models)."""
    
    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float):
        super().__init__()
        
        from model.attention import MultiHeadAttention
        
        self.self_attention = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        
        self.feed_forward = FeedForward(d_model, d_ff, dropout)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # Self-attention with residual
        attn_out = self.self_attention(x, x, x, mask)
        x = self.norm1(x + self.dropout1(attn_out))
        
        # Feed-forward with residual
        ff_out = self.feed_forward(x)
        x = self.norm2(x + self.dropout2(ff_out))
        
        return x


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Complete Transformer Model")
    print("=" * 60)
    
    # Create model
    model = Transformer(
        src_vocab_size=10000,
        tgt_vocab_size=10000,
        d_model=512,
        n_heads=8,
        n_encoder_layers=6,
        n_decoder_layers=6,
        d_ff=2048,
        dropout=0.1
    )
    
    print(f"\nModel Parameters: {model.count_parameters():,}")
    
    # Test forward pass
    src = torch.randint(1, 10000, (2, 20))  # batch=2, src_len=20
    tgt = torch.randint(1, 10000, (2, 15))  # batch=2, tgt_len=15
    
    print(f"\nSource shape: {src.shape}")
    print(f"Target shape: {tgt.shape}")
    
    logits = model(src, tgt)
    print(f"Output logits shape: {logits.shape}")
    
    # Test generation
    print("\nTesting generation...")
    generated = model.generate(src[:1], max_len=20, start_token=1, end_token=2)
    print(f"Generated shape: {generated.shape}")
    print(f"Generated tokens: {generated[0].tolist()}")
    
    print("\n" + "=" * 60)
    print("Testing Encoder-Only Model")
    print("=" * 60)
    
    encoder_model = TransformerEncoderOnly(
        vocab_size=10000,
        d_model=256,
        n_heads=4,
        n_layers=4,
        num_classes=5
    )
    
    x = torch.randint(1, 10000, (2, 50))
    output = encoder_model(x)
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {output.shape}")
    
    print("\n" + "=" * 60)
    print("Testing Decoder-Only Model (GPT-style)")
    print("=" * 60)
    
    decoder_model = TransformerDecoderOnly(
        vocab_size=10000,
        d_model=256,
        n_heads=4,
        n_layers=4
    )
    
    x = torch.randint(1, 10000, (2, 50))
    output = decoder_model(x)
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {output.shape}")
    
    print("\n✅ All Transformer tests passed!")
