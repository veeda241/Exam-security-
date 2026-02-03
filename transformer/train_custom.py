"""
Custom Training Script - Modify this for your project

This template shows how to train the Transformer on your own data.
"""

import argparse
import torch
from pathlib import Path

from config import TransformerConfig, TinyTransformerConfig, SmallTransformerConfig
from model import Transformer
from data.tokenizer import SimpleTokenizer, BPETokenizer
from data.dataset import TranslationDataset, LanguageModelingDataset, create_translation_dataloaders
from training.trainer import Trainer, create_optimizer
from training.scheduler import CosineAnnealingWarmup
from training.losses import LabelSmoothingLoss


# =============================================================================
# STEP 1: LOAD YOUR DATA
# =============================================================================

def load_your_data(data_path: str):
    """
    Modify this function to load YOUR dataset.
    
    For Translation (Seq2Seq):
        Return: src_texts, tgt_texts (lists of strings)
        
    For Language Modeling:
        Return: texts (list of strings)
        
    For Classification:
        Return: texts, labels (lists)
    """
    
    # Example: Load from files
    # with open(f"{data_path}/source.txt", "r", encoding="utf-8") as f:
    #     src_texts = f.read().strip().split("\n")
    # with open(f"{data_path}/target.txt", "r", encoding="utf-8") as f:
    #     tgt_texts = f.read().strip().split("\n")
    
    # Example: Load from CSV
    # import pandas as pd
    # df = pd.read_csv(f"{data_path}/data.csv")
    # src_texts = df["source"].tolist()
    # tgt_texts = df["target"].tolist()
    
    # Example: Load from JSON
    # import json
    # with open(f"{data_path}/data.json", "r") as f:
    #     data = json.load(f)
    # src_texts = [item["src"] for item in data]
    # tgt_texts = [item["tgt"] for item in data]
    
    # Demo data (replace with your actual data loading)
    src_texts = [
        "Hello world",
        "How are you",
        "Machine learning is powerful",
    ] * 100
    
    tgt_texts = [
        "Bonjour monde",
        "Comment allez vous",
        "L apprentissage automatique est puissant",
    ] * 100
    
    return src_texts, tgt_texts


# =============================================================================
# STEP 2: CONFIGURE YOUR MODEL
# =============================================================================

def get_model_config(config_name: str):
    """
    Choose or customize your model configuration.
    """
    
    configs = {
        "tiny": TinyTransformerConfig,    # ~1M params - for testing
        "small": SmallTransformerConfig,  # ~10M params - for small datasets
        "base": TransformerConfig,        # ~65M params - for larger datasets
    }
    
    # Or create a custom config:
    # from dataclasses import dataclass
    # @dataclass
    # class CustomConfig:
    #     vocab_size: int = 50000
    #     d_model: int = 768
    #     n_heads: int = 12
    #     n_encoder_layers: int = 12
    #     n_decoder_layers: int = 12
    #     d_ff: int = 3072
    #     max_seq_len: int = 1024
    #     dropout: float = 0.1
    
    return configs.get(config_name, TinyTransformerConfig)


# =============================================================================
# MAIN TRAINING FUNCTION
# =============================================================================

def train(args):
    """Main training loop."""
    
    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Get config
    config = get_model_config(args.config)
    print(f"\nModel Configuration: {args.config}")
    print(f"  d_model: {config.d_model}")
    print(f"  n_heads: {config.n_heads}")
    print(f"  layers: {config.n_encoder_layers}")
    
    # ==========================================================================
    # Load your data
    # ==========================================================================
    print("\n📂 Loading data...")
    src_texts, tgt_texts = load_your_data(args.data_path)
    
    # Split into train/val
    split_idx = int(len(src_texts) * 0.9)
    train_src, val_src = src_texts[:split_idx], src_texts[split_idx:]
    train_tgt, val_tgt = tgt_texts[:split_idx], tgt_texts[split_idx:]
    
    print(f"  Training samples: {len(train_src)}")
    print(f"  Validation samples: {len(val_src)}")
    
    # ==========================================================================
    # Create tokenizers
    # ==========================================================================
    print("\n🔤 Building tokenizers...")
    
    # Option 1: Simple word tokenizer (fast, good for testing)
    src_tokenizer = SimpleTokenizer(vocab_size=config.vocab_size, min_freq=1)
    tgt_tokenizer = SimpleTokenizer(vocab_size=config.vocab_size, min_freq=1)
    src_tokenizer.build_vocab(src_texts)
    tgt_tokenizer.build_vocab(tgt_texts)
    
    # Option 2: BPE tokenizer (better for production)
    # src_tokenizer = BPETokenizer(vocab_size=config.vocab_size)
    # src_tokenizer.train_from_texts(src_texts)
    # tgt_tokenizer = BPETokenizer(vocab_size=config.vocab_size)
    # tgt_tokenizer.train_from_texts(tgt_texts)
    
    print(f"  Source vocab: {len(src_tokenizer)} tokens")
    print(f"  Target vocab: {len(tgt_tokenizer)} tokens")
    
    # Save tokenizers for inference later
    src_tokenizer.save("checkpoints/src_tokenizer.json")
    tgt_tokenizer.save("checkpoints/tgt_tokenizer.json")
    
    # ==========================================================================
    # Create data loaders
    # ==========================================================================
    print("\n📊 Creating data loaders...")
    train_loader, val_loader = create_translation_dataloaders(
        train_src, train_tgt,
        val_src, val_tgt,
        src_tokenizer, tgt_tokenizer,
        batch_size=args.batch_size,
        max_src_len=config.max_seq_len,
        max_tgt_len=config.max_seq_len
    )
    
    # ==========================================================================
    # Create model
    # ==========================================================================
    print("\n🏗️ Creating model...")
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
    
    print(f"  Parameters: {model.count_parameters():,}")
    
    # ==========================================================================
    # Create optimizer & scheduler
    # ==========================================================================
    optimizer = create_optimizer(
        model,
        optimizer_name="adamw",
        lr=args.lr,
        weight_decay=0.01
    )
    
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * 0.1)
    
    scheduler = CosineAnnealingWarmup(
        optimizer,
        warmup_steps=warmup_steps,
        total_steps=total_steps
    )
    
    # ==========================================================================
    # Create loss function
    # ==========================================================================
    criterion = LabelSmoothingLoss(
        vocab_size=len(tgt_tokenizer),
        smoothing=0.1,
        ignore_index=0  # Padding token
    )
    
    # ==========================================================================
    # Create trainer
    # ==========================================================================
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
    
    # ==========================================================================
    # Train!
    # ==========================================================================
    print("\n🚀 Starting training...")
    print("=" * 60)
    
    history = trainer.train(num_epochs=args.epochs)
    
    # ==========================================================================
    # Test generation
    # ==========================================================================
    print("\n" + "=" * 60)
    print("🧪 Testing generation...")
    
    model.eval()
    test_sentence = train_src[0]  # Use first training example
    src_ids = torch.tensor([src_tokenizer.encode(test_sentence)]).to(device)
    
    with torch.no_grad():
        generated = model.generate(
            src_ids,
            max_len=50,
            start_token=tgt_tokenizer.bos_token_id,
            end_token=tgt_tokenizer.eos_token_id,
            temperature=0.8
        )
        
    generated_text = tgt_tokenizer.decode(generated[0].tolist())
    print(f"  Input: {test_sentence}")
    print(f"  Generated: {generated_text}")
    
    print("\n✅ Training complete!")
    print(f"📁 Checkpoints saved to: {args.checkpoint_dir}")
    print(f"📊 Logs saved to: {args.log_dir}")
    print(f"\n💡 To view training logs: tensorboard --logdir {args.log_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train Transformer on Custom Data")
    
    # Data
    parser.add_argument('--data_path', type=str, default='./data',
                        help='Path to your data directory')
    
    # Model
    parser.add_argument('--config', type=str, default='tiny',
                        choices=['tiny', 'small', 'base'],
                        help='Model configuration')
    
    # Training
    parser.add_argument('--epochs', type=int, default=20,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='Learning rate')
    parser.add_argument('--gradient_accumulation', type=int, default=1,
                        help='Gradient accumulation steps')
    parser.add_argument('--mixed_precision', action='store_true',
                        help='Use mixed precision (FP16)')
    parser.add_argument('--patience', type=int, default=5,
                        help='Early stopping patience')
    
    # Paths
    parser.add_argument('--checkpoint_dir', type=str, default='./checkpoints',
                        help='Directory to save checkpoints')
    parser.add_argument('--log_dir', type=str, default='./logs',
                        help='Directory for TensorBoard logs')
    
    args = parser.parse_args()
    
    # Create directories
    Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    
    train(args)


if __name__ == "__main__":
    main()
