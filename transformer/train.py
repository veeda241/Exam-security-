"""
Main Training Script for Transformer

Usage:
    python train.py --config tiny  # For testing
    python train.py --config small # For small model
    python train.py --config base  # For base model
"""

import argparse
import torch
import torch.nn as nn
from pathlib import Path

from config import TransformerConfig, TinyTransformerConfig, SmallTransformerConfig
from model import Transformer
from data.tokenizer import SimpleTokenizer
from data.dataset import TranslationDataset, create_translation_dataloaders
from training.trainer import Trainer, create_optimizer
from training.scheduler import CosineAnnealingWarmup
from training.losses import LabelSmoothingLoss


def get_sample_data():
    """Get sample data for testing."""
    # Simple English-French translation pairs
    src_texts = [
        "Hello world",
        "How are you",
        "I am fine thank you",
        "Good morning",
        "What is your name",
        "My name is John",
        "Nice to meet you",
        "Goodbye",
        "See you later",
        "Have a nice day",
        "The weather is nice today",
        "I like to read books",
        "She is my friend",
        "We are learning",
        "This is interesting",
        "The cat is sleeping",
        "I love programming",
        "Machine learning is fun",
        "Deep learning models",
        "Neural networks are powerful",
    ] * 10  # Repeat for more data
    
    tgt_texts = [
        "Bonjour monde",
        "Comment allez vous",
        "Je vais bien merci",
        "Bonjour",
        "Quel est votre nom",
        "Je m appelle John",
        "Ravi de vous rencontrer",
        "Au revoir",
        "A plus tard",
        "Bonne journee",
        "Il fait beau aujourd hui",
        "J aime lire des livres",
        "Elle est mon amie",
        "Nous apprenons",
        "C est interessant",
        "Le chat dort",
        "J aime programmer",
        "L apprentissage automatique est amusant",
        "Modeles d apprentissage profond",
        "Les reseaux neuronaux sont puissants",
    ] * 10
    
    return src_texts, tgt_texts


def train(args):
    """Main training function."""
    
    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Get configuration
    if args.config == "tiny":
        config = TinyTransformerConfig
    elif args.config == "small":
        config = SmallTransformerConfig
    else:
        config = TransformerConfig
        
    print(f"\nConfiguration: {args.config}")
    print(f"  d_model: {config.d_model}")
    print(f"  n_heads: {config.n_heads}")
    print(f"  n_layers: {config.n_encoder_layers}")
    print(f"  d_ff: {config.d_ff}")
    
    # Get data
    print("\nLoading data...")
    src_texts, tgt_texts = get_sample_data()
    
    # Split data
    split_idx = int(len(src_texts) * 0.9)
    train_src, val_src = src_texts[:split_idx], src_texts[split_idx:]
    train_tgt, val_tgt = tgt_texts[:split_idx], tgt_texts[split_idx:]
    
    print(f"  Training samples: {len(train_src)}")
    print(f"  Validation samples: {len(val_src)}")
    
    # Create tokenizers
    print("\nBuilding tokenizers...")
    src_tokenizer = SimpleTokenizer(vocab_size=config.vocab_size, min_freq=1)
    tgt_tokenizer = SimpleTokenizer(vocab_size=config.vocab_size, min_freq=1)
    
    src_tokenizer.build_vocab(src_texts)
    tgt_tokenizer.build_vocab(tgt_texts)
    
    print(f"  Source vocab size: {len(src_tokenizer)}")
    print(f"  Target vocab size: {len(tgt_tokenizer)}")
    
    # Create data loaders
    print("\nCreating data loaders...")
    train_loader, val_loader = create_translation_dataloaders(
        train_src, train_tgt,
        val_src, val_tgt,
        src_tokenizer, tgt_tokenizer,
        batch_size=args.batch_size,
        max_src_len=config.max_seq_len,
        max_tgt_len=config.max_seq_len
    )
    
    # Create model
    print("\nCreating model...")
    model = Transformer(
        src_vocab_size=len(src_tokenizer),
        tgt_vocab_size=len(tgt_tokenizer),
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_encoder_layers=config.n_encoder_layers,
        n_decoder_layers=config.n_decoder_layers,
        d_ff=config.d_ff,
        max_seq_len=config.max_seq_len,
        dropout=config.dropout,
        pad_token=0
    )
    
    print(f"  Model parameters: {model.count_parameters():,}")
    
    # Create optimizer
    optimizer = create_optimizer(
        model,
        optimizer_name="adamw",
        lr=args.lr,
        weight_decay=0.01
    )
    
    # Create scheduler
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * 0.1)
    
    scheduler = CosineAnnealingWarmup(
        optimizer,
        warmup_steps=warmup_steps,
        total_steps=total_steps
    )
    
    # Create loss function
    criterion = LabelSmoothingLoss(
        vocab_size=len(tgt_tokenizer),
        smoothing=0.1,
        ignore_index=0
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        train_loader=train_loader,
        val_loader=val_loader,
        scheduler=scheduler,
        device=device,
        checkpoint_dir=args.checkpoint_dir,
        log_dir=args.log_dir,
        gradient_accumulation_steps=args.gradient_accumulation,
        mixed_precision=args.mixed_precision,
        early_stopping_patience=args.patience
    )
    
    # Train
    print("\nStarting training...")
    print("=" * 60)
    
    history = trainer.train(num_epochs=args.epochs)
    
    # Test generation
    print("\n" + "=" * 60)
    print("Testing generation...")
    
    model.eval()
    test_sentence = "Hello world"
    src_ids = torch.tensor([src_tokenizer.encode(test_sentence)]).to(device)
    
    with torch.no_grad():
        generated = model.generate(
            src_ids,
            max_len=50,
            start_token=tgt_tokenizer.bos_token_id,
            end_token=tgt_tokenizer.eos_token_id
        )
        
    generated_text = tgt_tokenizer.decode(generated[0].tolist())
    print(f"  Input: {test_sentence}")
    print(f"  Generated: {generated_text}")
    
    print("\n✅ Training complete!")
    print(f"Best validation loss: {trainer.best_val_loss:.4f}")
    print(f"Checkpoints saved to: {args.checkpoint_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train Transformer Model")
    
    # Model config
    parser.add_argument('--config', type=str, default='tiny',
                        choices=['tiny', 'small', 'base'],
                        help='Model configuration')
    
    # Training params
    parser.add_argument('--epochs', type=int, default=10,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='Learning rate')
    parser.add_argument('--gradient_accumulation', type=int, default=1,
                        help='Gradient accumulation steps')
    parser.add_argument('--mixed_precision', action='store_true',
                        help='Use mixed precision training')
    parser.add_argument('--patience', type=int, default=5,
                        help='Early stopping patience')
    
    # Paths
    parser.add_argument('--checkpoint_dir', type=str, default='./checkpoints',
                        help='Checkpoint directory')
    parser.add_argument('--log_dir', type=str, default='./logs',
                        help='Log directory')
    
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
