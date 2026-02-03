# Transformer from Scratch

A complete implementation of the Transformer architecture in PyTorch, built step by step.

## Project Structure

```
transformer/
├── model/
│   ├── __init__.py
│   ├── embeddings.py       # Token + Positional Embeddings
│   ├── attention.py        # Self-Attention & Multi-Head Attention
│   ├── encoder.py          # Encoder Block & Stack
│   ├── decoder.py          # Decoder Block & Stack
│   ├── transformer.py      # Full Transformer Model
│   └── utils.py            # Masks, Layer Norm, etc.
├── data/
│   ├── __init__.py
│   ├── tokenizer.py        # BPE/WordPiece Tokenizer
│   ├── dataset.py          # Dataset & DataLoader
│   └── preprocessing.py    # Text cleaning & preparation
├── training/
│   ├── __init__.py
│   ├── trainer.py          # Training loop
│   ├── optimizer.py        # Adam with warmup
│   └── loss.py             # Cross-entropy with label smoothing
├── config.py               # Model configuration
├── train.py                # Main training script
├── inference.py            # Generate text
└── requirements.txt        # Dependencies
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Train model
python train.py

# Generate text
python inference.py --prompt "Hello world"
```

## Architecture Overview

1. **Input Embedding** → Convert tokens to vectors
2. **Positional Encoding** → Add position information
3. **Encoder Stack** → Process input sequence
4. **Decoder Stack** → Generate output sequence
5. **Output Layer** → Predict next token

## Requirements

- Python 3.8+
- PyTorch 2.0+
- CUDA (recommended for training)
