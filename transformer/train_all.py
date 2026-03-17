"""
ExamGuard Pro - Unified Transformer Training
Trains three models from the project's architecture:
  1. URL Risk Classifier          - classifies URLs into 8 risk categories
  2. Behavioral Anomaly Detector  - detects cheating from event sequences
  3. Screen Content Classifier    - classifies screenshot/OCR text by risk

Usage:
    python train_all.py                     # Train all models
    python train_all.py --task url          # Train URL classifier only
    python train_all.py --task behavior     # Train behavioral model only
    python train_all.py --task screen       # Train screen content model only
    python train_all.py --epochs 20         # Custom epochs
"""

import argparse
import json
import sys
import os
import random
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from config import SmallTransformerConfig
from model import Transformer
from data.tokenizer import SimpleTokenizer
from training.scheduler import CosineAnnealingWarmup
from generate_data import (
    generate_url_dataset,
    generate_behavior_dataset,
    generate_screen_content_dataset,
    EVENT_TYPES,
    EVENT_TO_ID,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


# ============================================================================
# TASK 1: URL RISK CLASSIFIER
# ============================================================================

NUM_URL_CLASSES = 8  # exam_platform, educational, search_engine, code_hosting,
#                      social_media, entertainment, ai_tool, cheating

CLASS_NAMES = [
    "exam_platform", "educational", "search_engine", "code_hosting",
    "social_media", "entertainment", "ai_tool", "cheating",
]


class URLClassifier(nn.Module):
    """Classifies URL text into risk categories using the Transformer encoder."""

    def __init__(self, transformer: Transformer, d_model: int = 256, num_classes: int = NUM_URL_CLASSES):
        super().__init__()
        self.transformer = transformer
        self.pool_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.1),
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


class URLDataset(Dataset):
    def __init__(self, samples: List[Dict], tokenizer: SimpleTokenizer, max_length: int = 64):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        tokens = self.tokenizer.encode(s["url"])[:self.max_length]
        tokens += [self.tokenizer.pad_token_id] * (self.max_length - len(tokens))
        return {
            "input_ids": torch.tensor(tokens, dtype=torch.long),
            "label": torch.tensor(s["label_id"], dtype=torch.long),
            "risk_score": torch.tensor(s["risk_score"], dtype=torch.float),
        }


def train_url_classifier(epochs: int = 15, batch_size: int = 32, lr: float = 3e-4):
    """Train the URL risk classifier."""
    print("\n" + "=" * 60)
    print("  TASK 1: URL Risk Classifier Training")
    print("=" * 60)

    # 1. Data
    url_data = generate_url_dataset()
    random.shuffle(url_data)
    split = int(len(url_data) * 0.85)
    train_data, val_data = url_data[:split], url_data[split:]
    print(f"Train: {len(train_data)}, Val: {len(val_data)} samples")

    # 2. Tokenizer
    all_texts = [s["url"] for s in url_data]
    tokenizer = SimpleTokenizer(vocab_size=8000, min_freq=1)
    tokenizer.build_vocab(all_texts)

    # 3. Model
    d_model = 256
    transformer = Transformer(
        src_vocab_size=len(tokenizer),
        tgt_vocab_size=len(tokenizer),
        d_model=d_model, n_heads=4,
        n_encoder_layers=4, n_decoder_layers=4,
        d_ff=512, max_seq_len=64,
        pad_token=tokenizer.pad_token_id,
    )
    model = URLClassifier(transformer, d_model=d_model).to(DEVICE)

    # Class weights (handle imbalanced categories)
    class_counts = [0] * NUM_URL_CLASSES
    for s in train_data:
        class_counts[s["label_id"]] += 1
    total = sum(class_counts)
    weights = torch.tensor(
        [total / max(c, 1) for c in class_counts], dtype=torch.float
    ).to(DEVICE)
    weights = weights / weights.sum() * NUM_URL_CLASSES

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingWarmup(optimizer, warmup_steps=100, total_steps=epochs * (len(train_data) // batch_size + 1))

    train_loader = DataLoader(URLDataset(train_data, tokenizer), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(URLDataset(val_data, tokenizer), batch_size=batch_size)

    # 4. Training loop
    best_acc = 0.0
    for epoch in range(epochs):
        model.train()
        total_loss, correct, total = 0, 0, 0
        for batch in train_loader:
            ids = batch["input_ids"].to(DEVICE)
            labels = batch["label"].to(DEVICE)
            logits = model(ids)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            correct += (logits.argmax(dim=1) == labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for batch in val_loader:
                ids = batch["input_ids"].to(DEVICE)
                labels = batch["label"].to(DEVICE)
                logits = model(ids)
                val_correct += (logits.argmax(dim=1) == labels).sum().item()
                val_total += labels.size(0)
        val_acc = val_correct / max(val_total, 1)

        print(f"Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(train_loader):.4f} | "
              f"Train Acc: {train_acc:.3f} | Val Acc: {val_acc:.3f}")

        if val_acc > best_acc:
            best_acc = val_acc
            save_dir = CHECKPOINT_DIR / "url_classifier"
            save_dir.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "vocab_size": len(tokenizer),
                    "d_model": d_model,
                    "n_layers": 4,
                    "n_heads": 4,
                    "d_ff": 512,
                    "num_classes": NUM_URL_CLASSES,
                    "class_names": CLASS_NAMES,
                },
            }, save_dir / "best_model.pt")
            tokenizer.save(str(save_dir / "tokenizer.json"))

    print(f"\nURL Classifier trained — Best Val Acc: {best_acc:.3f}")
    print(f"Saved to {CHECKPOINT_DIR / 'url_classifier'}")
    return best_acc


# ============================================================================
# TASK 2: BEHAVIORAL ANOMALY DETECTION
# ============================================================================

NUM_BEHAVIOR_CLASSES = 4  # normal, mild, high, critical
BEHAVIOR_CLASS_NAMES = ["normal", "mild", "high", "critical"]

# Token vocabulary for event sequences
PAD_TOKEN = 0
UNK_TOKEN = 1
BOS_TOKEN = 2
EOS_TOKEN = 3
EVENT_VOCAB_SIZE = len(EVENT_TYPES) + 4  # events + special tokens


class BehavioralAnomalyDetector(nn.Module):
    """Classifies sequences of student events into risk levels."""

    def __init__(self, vocab_size: int = EVENT_VOCAB_SIZE, d_model: int = 128,
                 n_heads: int = 4, n_layers: int = 3, max_seq_len: int = 80,
                 num_classes: int = NUM_BEHAVIOR_CLASSES):
        super().__init__()
        self.d_model = d_model
        self.event_embedding = nn.Embedding(vocab_size, d_model, padding_idx=PAD_TOKEN)
        self.interval_proj = nn.Linear(1, d_model)
        self.pos_embedding = nn.Embedding(max_seq_len, d_model)
        self.combine = nn.Linear(d_model * 2, d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 2,
            dropout=0.1, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(d_model, num_classes),
        )

    def forward(self, event_ids: torch.Tensor, intervals: torch.Tensor) -> torch.Tensor:
        # event_ids: (B, S), intervals: (B, S, 1)
        B, S = event_ids.shape
        positions = torch.arange(S, device=event_ids.device).unsqueeze(0).expand(B, -1)

        evt_emb = self.event_embedding(event_ids) + self.pos_embedding(positions)
        int_emb = self.interval_proj(intervals)
        combined = self.combine(torch.cat([evt_emb, int_emb], dim=-1))

        pad_mask = (event_ids == PAD_TOKEN)
        encoded = self.encoder(combined, src_key_padding_mask=pad_mask)

        # Mean pool over non-padded positions
        mask = (~pad_mask).float().unsqueeze(-1)
        pooled = (encoded * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        return self.classifier(pooled)


class BehavioralDataset(Dataset):
    def __init__(self, samples: List[Dict], max_seq_len: int = 80):
        self.samples = samples
        self.max_seq_len = max_seq_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        events = s["events"]

        # Convert events to token IDs and intervals
        event_ids = []
        intervals = []
        for e in events[:self.max_seq_len]:
            eid = EVENT_TO_ID.get(e["event"], UNK_TOKEN)
            event_ids.append(eid)
            intervals.append(min(e.get("interval_ms", 2000) / 10000.0, 1.0))  # Normalize

        # Pad
        pad_len = self.max_seq_len - len(event_ids)
        event_ids += [PAD_TOKEN] * pad_len
        intervals += [0.0] * pad_len

        return {
            "event_ids": torch.tensor(event_ids, dtype=torch.long),
            "intervals": torch.tensor(intervals, dtype=torch.float).unsqueeze(-1),
            "label": torch.tensor(s["risk_label"], dtype=torch.long),
        }


def train_behavioral(epochs: int = 20, batch_size: int = 32, lr: float = 3e-4):
    """Train the behavioral anomaly detection model."""
    print("\n" + "=" * 60)
    print("  TASK 2: Behavioral Anomaly Detection Training")
    print("=" * 60)

    # 1. Data
    data = generate_behavior_dataset(n_per_class=300)
    random.shuffle(data)
    split = int(len(data) * 0.85)
    train_data, val_data = data[:split], data[split:]
    print(f"Train: {len(train_data)}, Val: {len(val_data)} sequences")

    # 2. Model
    model = BehavioralAnomalyDetector().to(DEVICE)

    # Class weights
    class_counts = [0] * NUM_BEHAVIOR_CLASSES
    for s in train_data:
        class_counts[s["risk_label"]] += 1
    total = sum(class_counts)
    weights = torch.tensor(
        [total / max(c, 1) for c in class_counts], dtype=torch.float
    ).to(DEVICE)
    weights = weights / weights.sum() * NUM_BEHAVIOR_CLASSES

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingWarmup(
        optimizer, warmup_steps=50,
        total_steps=epochs * (len(train_data) // batch_size + 1),
    )

    train_loader = DataLoader(BehavioralDataset(train_data), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(BehavioralDataset(val_data), batch_size=batch_size)

    # 3. Training loop
    best_acc = 0.0
    for epoch in range(epochs):
        model.train()
        total_loss, correct, total_n = 0, 0, 0
        for batch in train_loader:
            eids = batch["event_ids"].to(DEVICE)
            intervals = batch["intervals"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            logits = model(eids, intervals)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            correct += (logits.argmax(dim=1) == labels).sum().item()
            total_n += labels.size(0)

        train_acc = correct / total_n

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for batch in val_loader:
                eids = batch["event_ids"].to(DEVICE)
                intervals = batch["intervals"].to(DEVICE)
                labels = batch["label"].to(DEVICE)
                logits = model(eids, intervals)
                val_correct += (logits.argmax(dim=1) == labels).sum().item()
                val_total += labels.size(0)
        val_acc = val_correct / max(val_total, 1)

        print(f"Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(train_loader):.4f} | "
              f"Train Acc: {train_acc:.3f} | Val Acc: {val_acc:.3f}")

        if val_acc > best_acc:
            best_acc = val_acc
            save_dir = CHECKPOINT_DIR / "behavioral"
            save_dir.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "event_vocab_size": EVENT_VOCAB_SIZE,
                    "d_model": 128,
                    "n_layers": 3,
                    "n_heads": 4,
                    "max_seq_len": 80,
                    "num_classes": NUM_BEHAVIOR_CLASSES,
                    "class_names": BEHAVIOR_CLASS_NAMES,
                    "event_to_id": EVENT_TO_ID,
                },
            }, save_dir / "best_model.pt")

    print(f"\nBehavioral model trained — Best Val Acc: {best_acc:.3f}")
    print(f"Saved to {CHECKPOINT_DIR / 'behavioral'}")
    return best_acc


# ============================================================================
# TASK 3: SCREEN CONTENT RISK CLASSIFICATION
# ============================================================================

NUM_SCREEN_CLASSES = 5  # exam_safe, low_risk, medium_risk, high_risk, critical_risk
SCREEN_CLASS_NAMES = ["exam_safe", "low_risk", "medium_risk", "high_risk", "critical_risk"]


class ScreenContentClassifier(nn.Module):
    """Classifies OCR/screenshot text into risk categories."""

    def __init__(self, transformer: Transformer, d_model: int = 256,
                 num_classes: int = NUM_SCREEN_CLASSES):
        super().__init__()
        self.transformer = transformer
        self.pool_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(0.1),
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


class ScreenContentDataset(Dataset):
    def __init__(self, samples: List[Dict], tokenizer: SimpleTokenizer, max_length: int = 64):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        tokens = self.tokenizer.encode(s["text"])[:self.max_length]
        tokens += [self.tokenizer.pad_token_id] * (self.max_length - len(tokens))
        return {
            "input_ids": torch.tensor(tokens, dtype=torch.long),
            "label": torch.tensor(s["risk_label"], dtype=torch.long),
        }


def train_screen_content(epochs: int = 15, batch_size: int = 32, lr: float = 3e-4):
    """Train the screen content risk classifier."""
    print("\n" + "=" * 60)
    print("  TASK 3: Screen Content Risk Classifier Training")
    print("=" * 60)

    # 1. Data
    data = generate_screen_content_dataset()
    random.shuffle(data)
    split = int(len(data) * 0.85)
    train_data, val_data = data[:split], data[split:]
    print(f"Train: {len(train_data)}, Val: {len(val_data)} samples")

    # 2. Tokenizer
    all_texts = [s["text"] for s in data]
    tokenizer = SimpleTokenizer(vocab_size=8000, min_freq=1)
    tokenizer.build_vocab(all_texts)

    # 3. Model
    d_model = 256
    transformer = Transformer(
        src_vocab_size=len(tokenizer),
        tgt_vocab_size=len(tokenizer),
        d_model=d_model, n_heads=4,
        n_encoder_layers=4, n_decoder_layers=4,
        d_ff=512, max_seq_len=64,
        pad_token=tokenizer.pad_token_id,
    )
    model = ScreenContentClassifier(transformer, d_model=d_model).to(DEVICE)

    # Class weights
    class_counts = [0] * NUM_SCREEN_CLASSES
    for s in train_data:
        class_counts[s["risk_label"]] += 1
    total = sum(class_counts)
    weights = torch.tensor(
        [total / max(c, 1) for c in class_counts], dtype=torch.float
    ).to(DEVICE)
    weights = weights / weights.sum() * NUM_SCREEN_CLASSES

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingWarmup(
        optimizer, warmup_steps=50,
        total_steps=epochs * (len(train_data) // batch_size + 1),
    )

    train_loader = DataLoader(ScreenContentDataset(train_data, tokenizer), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(ScreenContentDataset(val_data, tokenizer), batch_size=batch_size)

    # 4. Training loop
    best_acc = 0.0
    for epoch in range(epochs):
        model.train()
        total_loss, correct, total_n = 0, 0, 0
        for batch in train_loader:
            ids = batch["input_ids"].to(DEVICE)
            labels = batch["label"].to(DEVICE)
            logits = model(ids)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            correct += (logits.argmax(dim=1) == labels).sum().item()
            total_n += labels.size(0)

        train_acc = correct / total_n

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for batch in val_loader:
                ids = batch["input_ids"].to(DEVICE)
                labels = batch["label"].to(DEVICE)
                logits = model(ids)
                val_correct += (logits.argmax(dim=1) == labels).sum().item()
                val_total += labels.size(0)
        val_acc = val_correct / max(val_total, 1)

        print(f"Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(train_loader):.4f} | "
              f"Train Acc: {train_acc:.3f} | Val Acc: {val_acc:.3f}")

        if val_acc > best_acc:
            best_acc = val_acc
            save_dir = CHECKPOINT_DIR / "screen_content"
            save_dir.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "vocab_size": len(tokenizer),
                    "d_model": d_model,
                    "n_layers": 4,
                    "n_heads": 4,
                    "d_ff": 512,
                    "num_classes": NUM_SCREEN_CLASSES,
                    "class_names": SCREEN_CLASS_NAMES,
                },
            }, save_dir / "best_model.pt")
            tokenizer.save(str(save_dir / "tokenizer.json"))

    print(f"\nScreen content classifier trained — Best Val Acc: {best_acc:.3f}")
    print(f"Saved to {CHECKPOINT_DIR / 'screen_content'}")
    return best_acc


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="ExamGuard Pro - Transformer Training")
    parser.add_argument("--task", choices=["url", "behavior", "screen", "all"], default="all",
                        help="Which model to train")
    parser.add_argument("--epochs", type=int, default=15, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    args = parser.parse_args()

    print(f"Device: {DEVICE}")
    print(f"PyTorch: {torch.__version__}")
    start = datetime.now()

    if args.task in ("url", "all"):
        train_url_classifier(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    if args.task in ("behavior", "all"):
        train_behavioral(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    if args.task in ("screen", "all"):
        train_screen_content(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    elapsed = datetime.now() - start
    print(f"\nTotal training time: {elapsed}")


if __name__ == "__main__":
    main()
