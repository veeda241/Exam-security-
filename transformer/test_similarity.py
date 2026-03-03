"""Quick test script to evaluate the trained similarity model."""

import torch
import torch.nn.functional as F
from pathlib import Path
import sys

# Add transformer to path
sys.path.insert(0, str(Path(__file__).parent))

from model import Transformer
from data.tokenizer import SimpleTokenizer

# Load tokenizer
tokenizer = SimpleTokenizer()
tokenizer.load(str(Path(__file__).parent / 'checkpoints/similarity/tokenizer.json'))
print(f"Tokenizer loaded with {len(tokenizer)} tokens")

# Load checkpoint
checkpoint = torch.load(
    Path(__file__).parent / 'checkpoints/similarity/best_model.pt',
    map_location='cpu'
)
print(f"\nCheckpoint loaded!")
print(f"Config: {checkpoint['config']}")
print(f"Epoch: {checkpoint['epoch']}")
print(f"Train loss: {checkpoint.get('train_loss', 'N/A')}")
print(f"Val loss: {checkpoint.get('val_loss', 'N/A')}")

# Load model
config = checkpoint['config']
transformer = Transformer(
    src_vocab_size=config['vocab_size'],
    tgt_vocab_size=config['vocab_size'],
    d_model=config['d_model'],
    n_heads=config['n_heads'],
    n_encoder_layers=config['n_layers'],
    n_decoder_layers=config['n_layers'],
    d_ff=config['d_ff'],
    max_seq_len=128,
    dropout=0.1,
    pad_token=tokenizer.pad_token_id
)

# Create projection layer (same as in training)
import torch.nn as nn
d_model = config['d_model']
projection = nn.Sequential(
    nn.Linear(d_model, d_model),
    nn.ReLU(),
    nn.Linear(d_model, d_model // 2),
)

# Load state dict for transformer only
transformer.load_state_dict(checkpoint['transformer_state_dict'])
transformer.eval()

print("\n" + "="*60)
print("SIMILARITY MODEL EVALUATION")
print("="*60)

def encode_text(text, max_len=128):
    """Encode text to embedding."""
    tokens = tokenizer.encode(text)[:max_len]
    tokens = tokens + [tokenizer.pad_token_id] * (max_len - len(tokens))
    input_ids = torch.tensor([tokens], dtype=torch.long)
    
    with torch.no_grad():
        encoder_out = transformer.encode(input_ids)
        
        # Mean pooling
        mask = (input_ids != tokenizer.pad_token_id).float().unsqueeze(-1)
        pooled = (encoder_out * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        
    return pooled

def compute_similarity(text1, text2):
    """Compute cosine similarity between two texts."""
    emb1 = encode_text(text1)
    emb2 = encode_text(text2)
    return F.cosine_similarity(emb1, emb2).item()

# Test cases
test_cases = [
    # High similarity (paraphrases)
    ("The mitochondria is the powerhouse of the cell.",
     "Mitochondria produce energy for cells."),
    
    # Medium similarity (related)
    ("Photosynthesis occurs in plant cells.",
     "Plants need sunlight to grow."),
    
    # Low similarity (different topics)
    ("DNA stores genetic information.",
     "The Renaissance was a cultural movement."),
    
    # Same text
    ("Hello world", "Hello world"),
    
    # Exam answer comparison
    ("The water cycle involves evaporation, condensation, and precipitation.",
     "Water evaporates, forms clouds, and falls as rain in a continuous cycle."),
]

for text1, text2 in test_cases:
    sim = compute_similarity(text1, text2)
    print(f"\nText 1: {text1[:50]}...")
    print(f"Text 2: {text2[:50]}...")
    print(f"Similarity: {sim:.4f}")
    
    if sim > 0.8:
        print("→ HIGH SIMILARITY (potential plagiarism)")
    elif sim > 0.5:
        print("→ MODERATE SIMILARITY")
    else:
        print("→ LOW SIMILARITY")

print("\n" + "="*60)
