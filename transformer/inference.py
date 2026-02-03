"""
Inference Script for Trained Transformer

Usage:
    python inference.py --checkpoint checkpoints/best.pt --input "Hello world"
"""

import argparse
import torch
from pathlib import Path

from config import TinyTransformerConfig
from model import Transformer
from data.tokenizer import SimpleTokenizer


def load_model_and_tokenizers(checkpoint_path: str, device: str = "cuda"):
    """Load trained model and tokenizers."""
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Get config (you may need to save this with checkpoint)
    config = TinyTransformerConfig
    
    # Create model
    model = Transformer(
        src_vocab_size=config.vocab_size,
        tgt_vocab_size=config.vocab_size,
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_encoder_layers=config.n_encoder_layers,
        n_decoder_layers=config.n_decoder_layers,
        d_ff=config.d_ff,
        max_seq_len=config.max_seq_len,
        dropout=0.0  # No dropout during inference
    ).to(device)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # Load tokenizers (you should save these with training)
    # For now, create dummy tokenizers
    src_tokenizer = SimpleTokenizer()
    tgt_tokenizer = SimpleTokenizer()
    
    return model, src_tokenizer, tgt_tokenizer


def translate(
    model,
    src_tokenizer,
    tgt_tokenizer,
    text: str,
    device: str = "cuda",
    max_len: int = 100,
    temperature: float = 1.0,
    top_k: int = None,
    top_p: float = None
) -> str:
    """Translate source text to target."""
    
    # Encode source
    src_ids = torch.tensor([src_tokenizer.encode(text)]).to(device)
    
    # Generate
    with torch.no_grad():
        generated = model.generate(
            src_ids,
            max_len=max_len,
            start_token=tgt_tokenizer.bos_token_id,
            end_token=tgt_tokenizer.eos_token_id,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p
        )
        
    # Decode
    output_text = tgt_tokenizer.decode(generated[0].tolist())
    
    return output_text


def interactive_mode(model, src_tokenizer, tgt_tokenizer, device):
    """Interactive translation mode."""
    
    print("\n" + "=" * 60)
    print("Interactive Translation Mode")
    print("Type 'quit' to exit")
    print("=" * 60 + "\n")
    
    while True:
        try:
            text = input("Input: ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not text:
                continue
                
            output = translate(model, src_tokenizer, tgt_tokenizer, text, device)
            print(f"Output: {output}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Transformer Inference")
    
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to model checkpoint')
    parser.add_argument('--input', type=str, default=None,
                        help='Input text to translate')
    parser.add_argument('--interactive', action='store_true',
                        help='Run in interactive mode')
    parser.add_argument('--temperature', type=float, default=1.0,
                        help='Sampling temperature')
    parser.add_argument('--top_k', type=int, default=None,
                        help='Top-k sampling')
    parser.add_argument('--top_p', type=float, default=None,
                        help='Top-p (nucleus) sampling')
    parser.add_argument('--max_len', type=int, default=100,
                        help='Maximum output length')
    
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load model
    print(f"Loading model from {args.checkpoint}...")
    model, src_tokenizer, tgt_tokenizer = load_model_and_tokenizers(
        args.checkpoint, device
    )
    print("Model loaded!")
    
    if args.interactive:
        interactive_mode(model, src_tokenizer, tgt_tokenizer, device)
    elif args.input:
        output = translate(
            model, src_tokenizer, tgt_tokenizer,
            args.input, device,
            max_len=args.max_len,
            temperature=args.temperature,
            top_k=args.top_k,
            top_p=args.top_p
        )
        print(f"Input: {args.input}")
        print(f"Output: {output}")
    else:
        print("Please provide --input or use --interactive mode")


if __name__ == "__main__":
    main()
