"""
Quick Test Script
Verifies all components work correctly.
"""

import torch
import sys

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from config import TransformerConfig, TinyTransformerConfig
        print("  ✓ config")
    except Exception as e:
        print(f"  ✗ config: {e}")
        return False
        
    try:
        from model import Transformer
        from model.embeddings import TokenEmbedding, PositionalEncoding, TransformerEmbedding
        from model.attention import MultiHeadAttention, ScaledDotProductAttention
        from model.encoder import Encoder, EncoderBlock
        from model.decoder import Decoder, DecoderBlock
        from model.transformer import TransformerEncoderOnly, TransformerDecoderOnly
        print("  ✓ model")
    except Exception as e:
        print(f"  ✗ model: {e}")
        return False
        
    try:
        from data.tokenizer import SimpleTokenizer, CharacterTokenizer
        from data.dataset import TranslationDataset, LanguageModelingDataset
        print("  ✓ data")
    except Exception as e:
        print(f"  ✗ data: {e}")
        return False
        
    try:
        from training.trainer import Trainer, create_optimizer
        from training.scheduler import WarmupScheduler, CosineAnnealingWarmup
        from training.losses import LabelSmoothingLoss
        print("  ✓ training")
    except Exception as e:
        print(f"  ✗ training: {e}")
        return False
        
    return True


def test_model():
    """Test model forward pass."""
    print("\nTesting model forward pass...")
    
    from model import Transformer
    
    # Create small model
    model = Transformer(
        src_vocab_size=1000,
        tgt_vocab_size=1000,
        d_model=64,
        n_heads=4,
        n_encoder_layers=2,
        n_decoder_layers=2,
        d_ff=128,
        max_seq_len=32,
        dropout=0.1
    )
    
    # Test forward pass
    src = torch.randint(1, 1000, (2, 10))
    tgt = torch.randint(1, 1000, (2, 8))
    
    try:
        logits = model(src, tgt)
        print(f"  ✓ Forward pass: {src.shape} + {tgt.shape} -> {logits.shape}")
    except Exception as e:
        print(f"  ✗ Forward pass: {e}")
        return False
        
    # Test generation
    try:
        model.eval()
        with torch.no_grad():
            generated = model.generate(src[:1], max_len=20, start_token=1, end_token=2)
        print(f"  ✓ Generation: {src[:1].shape} -> {generated.shape}")
    except Exception as e:
        print(f"  ✗ Generation: {e}")
        return False
        
    print(f"  Total parameters: {model.count_parameters():,}")
    
    return True


def test_tokenizer():
    """Test tokenizer."""
    print("\nTesting tokenizer...")
    
    from data.tokenizer import SimpleTokenizer
    
    tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    texts = ["Hello world", "How are you", "I am fine"]
    
    try:
        tokenizer.build_vocab(texts)
        print(f"  ✓ Vocab built: {len(tokenizer)} tokens")
    except Exception as e:
        print(f"  ✗ Vocab build: {e}")
        return False
        
    try:
        encoded = tokenizer.encode("Hello world")
        decoded = tokenizer.decode(encoded)
        print(f"  ✓ Encode/Decode: 'Hello world' -> {encoded} -> '{decoded}'")
    except Exception as e:
        print(f"  ✗ Encode/Decode: {e}")
        return False
        
    return True


def test_dataset():
    """Test dataset."""
    print("\nTesting dataset...")
    
    from data.tokenizer import SimpleTokenizer
    from data.dataset import TranslationDataset
    
    tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    src_texts = ["Hello world", "How are you"]
    tgt_texts = ["Bonjour monde", "Comment allez vous"]
    
    tokenizer.build_vocab(src_texts + tgt_texts)
    
    try:
        dataset = TranslationDataset(
            src_texts, tgt_texts,
            tokenizer, tokenizer,
            max_src_len=32, max_tgt_len=32
        )
        sample = dataset[0]
        print(f"  ✓ Dataset created: {len(dataset)} samples")
        print(f"  ✓ Sample shapes: src={sample['src'].shape}, tgt={sample['tgt'].shape}")
    except Exception as e:
        print(f"  ✗ Dataset: {e}")
        return False
        
    return True


def test_training_components():
    """Test training components."""
    print("\nTesting training components...")
    
    from training.losses import LabelSmoothingLoss
    from training.scheduler import CosineAnnealingWarmup
    
    # Test loss
    try:
        criterion = LabelSmoothingLoss(vocab_size=1000, smoothing=0.1)
        logits = torch.randn(32, 1000)
        targets = torch.randint(1, 1000, (32,))
        loss = criterion(logits, targets)
        print(f"  ✓ LabelSmoothingLoss: {loss.item():.4f}")
    except Exception as e:
        print(f"  ✗ LabelSmoothingLoss: {e}")
        return False
        
    # Test scheduler
    try:
        model = torch.nn.Linear(10, 10)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        scheduler = CosineAnnealingWarmup(optimizer, warmup_steps=100, total_steps=1000)
        
        for _ in range(10):
            scheduler.step()
        print(f"  ✓ CosineAnnealingWarmup: LR = {scheduler.get_lr()[0]:.2e}")
    except Exception as e:
        print(f"  ✗ CosineAnnealingWarmup: {e}")
        return False
        
    return True


def main():
    print("=" * 60)
    print("Transformer From Scratch - Quick Test")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_model()
    all_passed &= test_tokenizer()
    all_passed &= test_dataset()
    all_passed &= test_training_components()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("\nYou can now train a model with:")
        print("  python train.py --config tiny --epochs 5")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
