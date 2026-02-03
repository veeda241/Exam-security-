"""
Example: Text Classification with Encoder-Only Transformer (BERT-style)

This example shows how to use the encoder-only architecture
for text classification tasks.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import random

from config import TinyTransformerConfig
from model.transformer import TransformerEncoderOnly
from data.tokenizer import SimpleTokenizer
from data.dataset import TextClassificationDataset
from training.trainer import Trainer, create_optimizer
from training.scheduler import CosineAnnealingWarmup


def main():
    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Sample sentiment data
    positive_texts = [
        "I love this product, it's amazing!",
        "Great quality and fast shipping.",
        "Excellent customer service, highly recommend.",
        "This is the best purchase I've ever made.",
        "Absolutely fantastic, exceeded expectations!",
        "Very happy with my purchase, thank you!",
        "Perfect fit and great value for money.",
        "Outstanding product, will buy again.",
        "Incredible quality, five stars!",
        "Love it, exactly what I needed.",
    ] * 20
    
    negative_texts = [
        "Terrible product, waste of money.",
        "Very disappointed with the quality.",
        "Does not work as advertised.",
        "Poor customer service, never again.",
        "Complete garbage, do not buy.",
        "Arrived broken and took forever to ship.",
        "Not worth the price at all.",
        "Worst purchase I've ever made.",
        "Product fell apart after one use.",
        "Extremely unhappy with this purchase.",
    ] * 20
    
    # Create dataset
    texts = positive_texts + negative_texts
    labels = [1] * len(positive_texts) + [0] * len(negative_texts)
    
    # Shuffle
    combined = list(zip(texts, labels))
    random.shuffle(combined)
    texts, labels = zip(*combined)
    texts, labels = list(texts), list(labels)
    
    # Create tokenizer
    print("\nBuilding tokenizer...")
    tokenizer = SimpleTokenizer(vocab_size=5000, min_freq=1)
    tokenizer.build_vocab(texts)
    print(f"Vocabulary size: {len(tokenizer)}")
    
    # Split data
    split_idx = int(len(texts) * 0.8)
    train_texts, val_texts = texts[:split_idx], texts[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]
    
    print(f"\nTraining samples: {len(train_texts)}")
    print(f"Validation samples: {len(val_texts)}")
    
    # Create datasets
    train_dataset = TextClassificationDataset(
        train_texts, train_labels, tokenizer, max_length=64
    )
    val_dataset = TextClassificationDataset(
        val_texts, val_labels, tokenizer, max_length=64
    )
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    # Create model
    print("\nCreating model...")
    config = TinyTransformerConfig
    
    model = TransformerEncoderOnly(
        vocab_size=len(tokenizer),
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_encoder_layers,
        d_ff=config.d_ff,
        max_seq_len=config.max_seq_len,
        dropout=config.dropout,
        num_classes=2,
        pooling="cls"
    )
    
    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {num_params:,}")
    
    # Create optimizer
    optimizer = create_optimizer(model, lr=2e-4)
    total_steps = len(train_loader) * 10
    scheduler = CosineAnnealingWarmup(
        optimizer,
        warmup_steps=50,
        total_steps=total_steps
    )
    
    # Loss function
    criterion = nn.CrossEntropyLoss()
    
    # Custom training loop for classification
    print("\nStarting training...")
    print("=" * 60)
    
    model.to(device)
    best_accuracy = 0.0
    
    for epoch in range(10):
        # Training
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            logits = model(input_ids)
            loss = criterion(logits, labels)
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            
            total_loss += loss.item()
            predictions = logits.argmax(dim=-1)
            correct += (predictions == labels).sum().item()
            total += labels.size(0)
            
        train_loss = total_loss / len(train_loader)
        train_acc = correct / total
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                labels = batch['labels'].to(device)
                
                logits = model(input_ids)
                predictions = logits.argmax(dim=-1)
                val_correct += (predictions == labels).sum().item()
                val_total += labels.size(0)
                
        val_acc = val_correct / val_total
        
        if val_acc > best_accuracy:
            best_accuracy = val_acc
            torch.save(model.state_dict(), "best_classifier.pt")
            
        print(f"Epoch {epoch + 1}/10 | "
              f"Train Loss: {train_loss:.4f} | "
              f"Train Acc: {train_acc:.2%} | "
              f"Val Acc: {val_acc:.2%}")
    
    print("\n" + "=" * 60)
    print(f"Best validation accuracy: {best_accuracy:.2%}")
    
    # Test on some examples
    print("\nTesting on examples...")
    model.eval()
    
    test_texts = [
        "This is amazing, I love it!",
        "Terrible quality, do not recommend.",
        "Pretty good overall, satisfied.",
        "Worst product ever, complete waste.",
    ]
    
    for text in test_texts:
        ids = torch.tensor([tokenizer.encode(text, max_length=64, padding=True)]).to(device)
        with torch.no_grad():
            logits = model(ids)
            pred = logits.argmax(dim=-1).item()
            prob = torch.softmax(logits, dim=-1)[0][pred].item()
            
        sentiment = "Positive" if pred == 1 else "Negative"
        print(f"  '{text}'")
        print(f"    -> {sentiment} ({prob:.1%} confidence)\n")
    
    print("✅ Classification example complete!")


if __name__ == "__main__":
    main()
