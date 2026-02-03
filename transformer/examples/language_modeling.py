"""
Example: Language Modeling with GPT-style Decoder-Only Transformer

This example shows how to train a simple language model using
the decoder-only architecture (similar to GPT).
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from config import TinyTransformerConfig
from model.transformer import TransformerDecoderOnly
from data.tokenizer import CharacterTokenizer
from data.dataset import LanguageModelingDataset
from training.trainer import Trainer, create_optimizer
from training.scheduler import CosineAnnealingWarmup


def main():
    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Sample text data
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning models can learn complex patterns.",
        "Transformers have revolutionized natural language processing.",
        "Attention is all you need for sequence modeling.",
        "Neural networks are universal function approximators.",
        "The transformer architecture uses self-attention mechanisms.",
        "Language models predict the next token in a sequence.",
        "Training large models requires significant compute resources.",
        "Transfer learning enables models to leverage pre-trained knowledge.",
    ] * 50  # Repeat for more data
    
    # Create character tokenizer
    print("\nBuilding character tokenizer...")
    tokenizer = CharacterTokenizer()
    tokenizer.build_vocab(texts)
    print(f"Vocabulary size: {len(tokenizer)}")
    
    # Create dataset
    print("\nCreating dataset...")
    dataset = LanguageModelingDataset(
        texts=texts,
        tokenizer=tokenizer,
        max_length=64,
        stride=32
    )
    print(f"Dataset size: {len(dataset)}")
    
    # Split into train/val
    train_size = int(len(dataset) * 0.9)
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size]
    )
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # Create model
    print("\nCreating model...")
    config = TinyTransformerConfig
    
    model = TransformerDecoderOnly(
        vocab_size=len(tokenizer),
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_decoder_layers,
        d_ff=config.d_ff,
        max_seq_len=config.max_seq_len,
        dropout=config.dropout
    )
    
    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {num_params:,}")
    
    # Create optimizer and scheduler
    optimizer = create_optimizer(model, lr=1e-3)
    total_steps = len(train_loader) * 20  # 20 epochs
    scheduler = CosineAnnealingWarmup(
        optimizer,
        warmup_steps=100,
        total_steps=total_steps
    )
    
    # Loss function
    criterion = nn.CrossEntropyLoss(ignore_index=tokenizer.pad_token_id)
    
    # Create trainer
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        train_loader=train_loader,
        val_loader=val_loader,
        scheduler=scheduler,
        device=device,
        checkpoint_dir="./checkpoints_lm",
        log_dir="./logs_lm",
        mixed_precision=False
    )
    
    # Train
    print("\nStarting training...")
    print("=" * 60)
    
    trainer.train(num_epochs=20)
    
    # Test generation
    print("\n" + "=" * 60)
    print("Testing text generation...")
    
    model.eval()
    
    # Generate from a prompt
    prompt = "The quick"
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    input_ids = torch.tensor([prompt_ids]).to(device)
    
    generated_ids = input_ids
    
    for _ in range(50):
        with torch.no_grad():
            logits = model(generated_ids)
            next_token_logits = logits[:, -1, :]
            probs = torch.softmax(next_token_logits / 0.8, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated_ids = torch.cat([generated_ids, next_token], dim=1)
            
    generated_text = tokenizer.decode(generated_ids[0].tolist())
    print(f"\nPrompt: '{prompt}'")
    print(f"Generated: '{generated_text}'")
    
    print("\n✅ Language modeling example complete!")


if __name__ == "__main__":
    main()
