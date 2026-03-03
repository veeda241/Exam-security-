"""
ExamGuard Pro - Specialized Transformer Training for Exam Security

This script trains a specialized Transformer model for detecting:
1. Plagiarism (text similarity)
2. Collusion (student-to-student copying)
3. Source attribution (e.g. from Wikipedia/Chegg styles)

It expands on the basic similarity training with specific academic integrity use cases.
"""


# Hardcode logging to file for debugging
print("Starting ExamGuard training script...", flush=True)
import torch
print("Imported torch", flush=True)
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import random
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import sys

print("Setting up path...", flush=True)
# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import TransformerConfig
from model import Transformer
from data.tokenizer import SimpleTokenizer
from training.scheduler import CosineAnnealingWarmup

print("Imports complete.", flush=True)


# Re-use components from train_similarity.py where possible or redefine locally
# We need SimilarityEncoder and ContrastiveLoss

class SimilarityEncoder(nn.Module):
    """Wrapper that uses Transformer encoder for text similarity."""
    
    def __init__(self, transformer: Transformer, pooling: str = 'mean', d_model: int = 256):
        super().__init__()
        self.transformer = transformer
        self.pooling = pooling
        self.d_model = d_model
        
        self.projection = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model // 2),
        )
    
    def encode(self, input_ids: torch.Tensor) -> torch.Tensor:
        encoder_output = self.transformer.encode(input_ids)
        mask = (input_ids != self.transformer.pad_token).float()
        
        if self.pooling == 'mean':
            mask_expanded = mask.unsqueeze(-1).expand(encoder_output.size())
            sum_embeddings = (encoder_output * mask_expanded).sum(dim=1)
            sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
            pooled = sum_embeddings / sum_mask
        elif self.pooling == 'cls':
            pooled = encoder_output[:, 0]
        else:
            # Default mean
            pooled = encoder_output.mean(dim=1)
            
        return self.projection(pooled)
    
    def forward(self, text1_ids: torch.Tensor, text2_ids: torch.Tensor):
        emb1 = self.encode(text1_ids)
        emb2 = self.encode(text2_ids)
        return emb1, emb2

class ContrastiveLoss(nn.Module):
    def __init__(self, margin: float = 0.3):
        super().__init__()
        self.margin = margin
    
    def forward(self, embeddings1: torch.Tensor, embeddings2: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        embeddings1 = F.normalize(embeddings1, p=2, dim=1)
        embeddings2 = F.normalize(embeddings2, p=2, dim=1)
        cos_sim = (embeddings1 * embeddings2).sum(dim=1)
        is_similar = (labels > 0.5).float()
        positive_loss = is_similar * (1 - cos_sim).pow(2)
        negative_loss = (1 - is_similar) * F.relu(cos_sim - self.margin).pow(2)
        return (positive_loss + negative_loss).mean()

class CosineSimilarityLoss(nn.Module):
    def forward(self, embeddings1: torch.Tensor, embeddings2: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        predicted_sim = F.cosine_similarity(embeddings1, embeddings2)
        return F.mse_loss(predicted_sim, targets)

class ExamGuardDataset(Dataset):
    def __init__(self, pairs, tokenizer, max_length=128):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        text1, text2, similarity = self.pairs[idx]
        tokens1 = self.tokenizer.encode(text1)[:self.max_length]
        tokens2 = self.tokenizer.encode(text2)[:self.max_length]
        tokens1 = tokens1 + [self.tokenizer.pad_token_id] * (self.max_length - len(tokens1))
        tokens2 = tokens2 + [self.tokenizer.pad_token_id] * (self.max_length - len(tokens2))
        return {
            'text1': torch.tensor(tokens1, dtype=torch.long),
            'text2': torch.tensor(tokens2, dtype=torch.long),
            'similarity': torch.tensor(similarity, dtype=torch.float)
        }

# --- DATA GENERATION ---

def generate_exam_data() -> List[Tuple[str, str, float]]:
    data = []
    
    # 1. Direct Plagiarism (High Similarity)
    # Examples of copy-paste with minor edits
    plagiarism_pairs = [
        ("The Supreme Court's decision in Marbury v. Madison established the principle of judicial review.",
         "Marbury v. Madison was the Supreme Court case that established the judicial review principle.", 0.95),
        ("Object-oriented programming (OOP) is based on the concept of 'objects', which can contain data and code.",
         "OOP relies on 'objects' that hold both code and data to structure software.", 0.9),
        ("Photosynthesis is the process used by plants to convert light energy into chemical energy.",
         "Plants convert light energy to chemical energy through a process called photosynthesis.", 0.95),
        ("The mitochondria is the powerhouse of the cell, generating most of the cell's supply of adenosine triphosphate (ATP).",
         "The powerhouse of the cell is the mitochondria, which creates most of the ATP supply.", 0.92),
    ]
    
    # 2. Paraphrasing (Medium-High Similarity)
    # Attempting to hide plagiarism by rewording
    paraphrase_pairs = [
        ("The Great Depression was a severe worldwide economic depression that took place mostly during the 1930s.",
         "During the 1930s, the world experienced a massive economic downturn known as the Great Depression.", 0.85),
        ("In Python, a list is a mutable sequence, meaning elements can be changed after creation.",
         "Lists in Python can be modified after they are made, making them mutable sequences.", 0.82),
        ("Newton's second law states that force is equal to mass times acceleration.",
         "F=ma is the equation representing Newton's second law of motion.", 0.88),
    ]
    
    # 3. Independent Answers (Medium-Low Similarity)
    # Same topic, but different structure/content - legitimate students
    independent_pairs = [
        ("The French Revolution was caused by social inequality and economic crisis.",
         "Key factors in the French Revolution included poor harvests and high taxes on the third estate.", 0.6),
        ("I believe the main theme of Hamlet is indecision and its consequences.",
         "Hamlet explores the complexity of revenge and madness through its protagonist.", 0.5),
        ("Normalization in databases reduces redundancy.",
         "We use normalization to ensure data integrity and minimize duplicate data.", 0.65),
    ]
    
    # 4. Different Topics (Low Similarity)
    # Completely unrelated
    different_pairs = [
        ("The French Revolution began in 1789.", 
         "Python uses indentation to define code blocks.", 0.05),
        ("Mitochondria produce ATP.", 
         "The Supreme Court has 9 justices.", 0.08),
        ("Igneous rocks are formed from cooling lava.", 
         "Supply and demand determine market prices.", 0.02),
    ]
    
    # 5. Suspicious "Online Source" markers (High Similarity context)
    online_source_pairs = [
        ("According to Wikipedia, the population of France is 67 million.",
         "The population of France is approximately 67 million.", 0.8),
        ("As stated in the Chegg solution, the derivative of x^2 is 2x.",
         "The derivative of x^2 is 2x.", 0.85),
    ]

    # Combine all
    data.extend(plagiarism_pairs)
    data.extend(paraphrase_pairs)
    data.extend(independent_pairs)
    data.extend(different_pairs)
    data.extend(online_source_pairs)
    
    # Symmetric augmentation
    augmented = []
    for t1, t2, s in data:
        augmented.append((t1, t2, s))
        augmented.append((t2, t1, s))
        # Simple noise augmentation
        augmented.append((t1.lower(), t2.lower(), s))
        
    return augmented

def train_examguard_model(epochs=10, batch_size=32):
    print("Initializing ExamGuard Training...")
    
    # 1. Prepare Data
    pairs = generate_exam_data()
    print(f"Generated {len(pairs)} training pairs.")
    
    # 2. Tokenizer
    all_text = [p[0] for p in pairs] + [p[1] for p in pairs]
    tokenizer = SimpleTokenizer(vocab_size=8000) # Slightly smaller vocab for speed
    tokenizer.build_vocab(all_text)
    
    # 3. Model Setup
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    
    d_model = 256
    transformer = Transformer(
        src_vocab_size=len(tokenizer),
        tgt_vocab_size=len(tokenizer),
        d_model=d_model,
        n_heads=4,
        n_encoder_layers=4,
        n_decoder_layers=4,
        d_ff=512,
        max_seq_len=128,
        pad_token=tokenizer.pad_token_id
    )
    model = SimilarityEncoder(transformer, d_model=d_model).to(device)
    
    # 4. Training Loop
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    criterion = ContrastiveLoss()
    mse = CosineSimilarityLoss()
    
    dataset = ExamGuardDataset(pairs, tokenizer)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    print("\nStarting Training Loop...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch in loader:
            t1 = batch['text1'].to(device)
            t2 = batch['text2'].to(device)
            sim = batch['similarity'].to(device)
            
            emb1, emb2 = model(t1, t2)
            
            loss_c = criterion(emb1, emb2, sim)
            loss_m = mse(emb1, emb2, sim)
            loss = loss_c + loss_m
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(loader)
        print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")
        
    # 5. Save
    save_dir = Path("transformer/checkpoints/similarity")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': {
            'vocab_size': len(tokenizer),
            'd_model': d_model,
            'n_layers': 4,
            'n_heads': 4,
            'd_ff': 512
        }
    }, save_dir / "best_model.pt")
    
    tokenizer.save(str(save_dir / "tokenizer.json"))
    print(f"\nModel saved to {save_dir}")

if __name__ == "__main__":
    train_examguard_model()
