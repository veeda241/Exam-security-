"""
Tokenizer Module
Simple character/word tokenizer and BPE tokenizer wrapper
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from collections import Counter
from pathlib import Path


class SimpleTokenizer:
    """
    Simple word-level tokenizer with basic preprocessing.
    
    Features:
    - Word-level tokenization
    - Special tokens (PAD, UNK, BOS, EOS)
    - Vocabulary building from corpus
    - Save/load functionality
    """
    
    # Special tokens
    PAD_TOKEN = "<pad>"
    UNK_TOKEN = "<unk>"
    BOS_TOKEN = "<bos>"
    EOS_TOKEN = "<eos>"
    
    def __init__(
        self,
        vocab_size: int = 30000,
        min_freq: int = 2,
        lowercase: bool = True
    ):
        """
        Args:
            vocab_size: Maximum vocabulary size
            min_freq: Minimum frequency for a token to be included
            lowercase: Convert text to lowercase
        """
        self.vocab_size = vocab_size
        self.min_freq = min_freq
        self.lowercase = lowercase
        
        # Special token IDs
        self.pad_token_id = 0
        self.unk_token_id = 1
        self.bos_token_id = 2
        self.eos_token_id = 3
        
        # Initialize vocabulary with special tokens
        self.token_to_id: Dict[str, int] = {
            self.PAD_TOKEN: 0,
            self.UNK_TOKEN: 1,
            self.BOS_TOKEN: 2,
            self.EOS_TOKEN: 3,
        }
        self.id_to_token: Dict[int, str] = {v: k for k, v in self.token_to_id.items()}
        
    def _preprocess(self, text: str) -> str:
        """Preprocess text before tokenization."""
        if self.lowercase:
            text = text.lower()
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text.strip())
        return text
        
    def _tokenize(self, text: str) -> List[str]:
        """Split text into tokens."""
        text = self._preprocess(text)
        # Simple word tokenization (split on whitespace and punctuation)
        tokens = re.findall(r'\b\w+\b|[^\w\s]', text)
        return tokens
        
    def build_vocab(self, texts: List[str]) -> None:
        """
        Build vocabulary from a list of texts.
        
        Args:
            texts: List of text strings
        """
        # Count token frequencies
        counter = Counter()
        for text in texts:
            tokens = self._tokenize(text)
            counter.update(tokens)
            
        # Sort by frequency and add to vocabulary
        most_common = counter.most_common(self.vocab_size - len(self.token_to_id))
        
        for token, freq in most_common:
            if freq >= self.min_freq and token not in self.token_to_id:
                idx = len(self.token_to_id)
                self.token_to_id[token] = idx
                self.id_to_token[idx] = token
                
        print(f"Vocabulary built: {len(self.token_to_id)} tokens")
        
    def encode(
        self,
        text: str,
        add_special_tokens: bool = True,
        max_length: Optional[int] = None,
        padding: bool = False
    ) -> List[int]:
        """
        Encode text to token IDs.
        
        Args:
            text: Input text
            add_special_tokens: Add BOS and EOS tokens
            max_length: Maximum sequence length (truncate if longer)
            padding: Pad to max_length
            
        Returns:
            List of token IDs
        """
        tokens = self._tokenize(text)
        
        # Convert to IDs
        token_ids = [
            self.token_to_id.get(token, self.unk_token_id)
            for token in tokens
        ]
        
        # Add special tokens
        if add_special_tokens:
            token_ids = [self.bos_token_id] + token_ids + [self.eos_token_id]
            
        # Truncate
        if max_length is not None:
            token_ids = token_ids[:max_length]
            
        # Pad
        if padding and max_length is not None:
            pad_length = max_length - len(token_ids)
            token_ids = token_ids + [self.pad_token_id] * pad_length
            
        return token_ids
    
    def decode(
        self,
        token_ids: List[int],
        skip_special_tokens: bool = True
    ) -> str:
        """
        Decode token IDs to text.
        
        Args:
            token_ids: List of token IDs
            skip_special_tokens: Skip special tokens in output
            
        Returns:
            Decoded text string
        """
        special_ids = {self.pad_token_id, self.bos_token_id, self.eos_token_id}
        
        tokens = []
        for token_id in token_ids:
            if skip_special_tokens and token_id in special_ids:
                continue
            token = self.id_to_token.get(token_id, self.UNK_TOKEN)
            tokens.append(token)
            
        # Simple detokenization
        text = ' '.join(tokens)
        # Fix punctuation spacing
        text = re.sub(r'\s([.,!?;:])', r'\1', text)
        return text
    
    def __len__(self) -> int:
        return len(self.token_to_id)
    
    @property
    def vocab_size_actual(self) -> int:
        return len(self.token_to_id)
    
    def save(self, path: str) -> None:
        """Save tokenizer to file."""
        data = {
            'vocab_size': self.vocab_size,
            'min_freq': self.min_freq,
            'lowercase': self.lowercase,
            'token_to_id': self.token_to_id,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    @classmethod
    def load(cls, path: str) -> 'SimpleTokenizer':
        """Load tokenizer from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        tokenizer = cls(
            vocab_size=data['vocab_size'],
            min_freq=data['min_freq'],
            lowercase=data['lowercase']
        )
        tokenizer.token_to_id = data['token_to_id']
        tokenizer.id_to_token = {int(v): k for k, v in data['token_to_id'].items()}
        
        return tokenizer


class BPETokenizer:
    """
    Byte-Pair Encoding (BPE) Tokenizer wrapper.
    
    Uses the `tokenizers` library for efficient BPE tokenization.
    """
    
    def __init__(self, vocab_size: int = 32000):
        """
        Args:
            vocab_size: Target vocabulary size
        """
        try:
            from tokenizers import Tokenizer
            from tokenizers.models import BPE
            from tokenizers.trainers import BpeTrainer
            from tokenizers.pre_tokenizers import Whitespace
            from tokenizers.processors import TemplateProcessing
        except ImportError:
            raise ImportError("Please install tokenizers: pip install tokenizers")
            
        self.vocab_size = vocab_size
        self._tokenizer = None
        
        # Special tokens
        self.pad_token = "<pad>"
        self.unk_token = "<unk>"
        self.bos_token = "<bos>"
        self.eos_token = "<eos>"
        
        self.special_tokens = [
            self.pad_token,
            self.unk_token,
            self.bos_token,
            self.eos_token,
        ]
        
    def train(self, files: List[str]) -> None:
        """
        Train BPE tokenizer on files.
        
        Args:
            files: List of file paths to train on
        """
        from tokenizers import Tokenizer
        from tokenizers.models import BPE
        from tokenizers.trainers import BpeTrainer
        from tokenizers.pre_tokenizers import Whitespace
        from tokenizers.processors import TemplateProcessing
        
        # Initialize tokenizer
        self._tokenizer = Tokenizer(BPE(unk_token=self.unk_token))
        self._tokenizer.pre_tokenizer = Whitespace()
        
        # Create trainer
        trainer = BpeTrainer(
            vocab_size=self.vocab_size,
            special_tokens=self.special_tokens,
            show_progress=True
        )
        
        # Train
        self._tokenizer.train(files, trainer)
        
        # Add post-processing (BOS/EOS tokens)
        self._tokenizer.post_processor = TemplateProcessing(
            single=f"{self.bos_token} $A {self.eos_token}",
            special_tokens=[
                (self.bos_token, self._tokenizer.token_to_id(self.bos_token)),
                (self.eos_token, self._tokenizer.token_to_id(self.eos_token)),
            ],
        )
        
        print(f"BPE Tokenizer trained: {self._tokenizer.get_vocab_size()} tokens")
        
    def train_from_texts(self, texts: List[str], temp_file: str = "temp_corpus.txt") -> None:
        """
        Train BPE tokenizer from a list of texts.
        
        Args:
            texts: List of text strings
            temp_file: Temporary file to write texts to
        """
        # Write texts to temporary file
        with open(temp_file, 'w', encoding='utf-8') as f:
            for text in texts:
                f.write(text + '\n')
                
        # Train on file
        self.train([temp_file])
        
        # Clean up
        Path(temp_file).unlink()
        
    def encode(
        self,
        text: str,
        max_length: Optional[int] = None,
        padding: bool = False
    ) -> List[int]:
        """
        Encode text to token IDs.
        
        Args:
            text: Input text
            max_length: Maximum sequence length
            padding: Pad to max_length
            
        Returns:
            List of token IDs
        """
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not trained. Call train() first.")
            
        encoded = self._tokenizer.encode(text)
        token_ids = encoded.ids
        
        # Truncate
        if max_length is not None:
            token_ids = token_ids[:max_length]
            
        # Pad
        if padding and max_length is not None:
            pad_id = self._tokenizer.token_to_id(self.pad_token)
            pad_length = max_length - len(token_ids)
            token_ids = token_ids + [pad_id] * pad_length
            
        return token_ids
    
    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """
        Decode token IDs to text.
        
        Args:
            token_ids: List of token IDs
            skip_special_tokens: Skip special tokens in output
            
        Returns:
            Decoded text string
        """
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not trained. Call train() first.")
            
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)
    
    @property
    def pad_token_id(self) -> int:
        return self._tokenizer.token_to_id(self.pad_token)
    
    @property
    def bos_token_id(self) -> int:
        return self._tokenizer.token_to_id(self.bos_token)
    
    @property
    def eos_token_id(self) -> int:
        return self._tokenizer.token_to_id(self.eos_token)
    
    def __len__(self) -> int:
        if self._tokenizer is None:
            return 0
        return self._tokenizer.get_vocab_size()
    
    def save(self, path: str) -> None:
        """Save tokenizer to file."""
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not trained.")
        self._tokenizer.save(path)
        
    @classmethod
    def load(cls, path: str) -> 'BPETokenizer':
        """Load tokenizer from file."""
        from tokenizers import Tokenizer
        
        tokenizer = cls()
        tokenizer._tokenizer = Tokenizer.from_file(path)
        return tokenizer


class CharacterTokenizer:
    """
    Character-level tokenizer.
    
    Useful for language modeling at character level.
    """
    
    def __init__(self):
        self.char_to_id: Dict[str, int] = {}
        self.id_to_char: Dict[int, str] = {}
        
        # Special tokens
        self.pad_token_id = 0
        self.unk_token_id = 1
        self.bos_token_id = 2
        self.eos_token_id = 3
        
        special_chars = ['<pad>', '<unk>', '<bos>', '<eos>']
        for i, char in enumerate(special_chars):
            self.char_to_id[char] = i
            self.id_to_char[i] = char
            
    def build_vocab(self, texts: List[str]) -> None:
        """Build character vocabulary from texts."""
        chars = set()
        for text in texts:
            chars.update(text)
            
        for char in sorted(chars):
            if char not in self.char_to_id:
                idx = len(self.char_to_id)
                self.char_to_id[char] = idx
                self.id_to_char[idx] = char
                
        print(f"Character vocabulary built: {len(self.char_to_id)} characters")
        
    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text to character IDs."""
        ids = [self.char_to_id.get(c, self.unk_token_id) for c in text]
        if add_special_tokens:
            ids = [self.bos_token_id] + ids + [self.eos_token_id]
        return ids
    
    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode character IDs to text."""
        special_ids = {self.pad_token_id, self.bos_token_id, self.eos_token_id}
        chars = []
        for i in ids:
            if skip_special_tokens and i in special_ids:
                continue
            chars.append(self.id_to_char.get(i, '<unk>'))
        return ''.join(chars)
    
    def __len__(self) -> int:
        return len(self.char_to_id)


if __name__ == "__main__":
    print("Testing SimpleTokenizer...")
    
    # Sample texts
    texts = [
        "Hello, how are you?",
        "I am fine, thank you!",
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is fascinating.",
    ]
    
    tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    tokenizer.build_vocab(texts)
    
    # Test encoding/decoding
    test_text = "Hello, how are you?"
    encoded = tokenizer.encode(test_text)
    decoded = tokenizer.decode(encoded)
    
    print(f"  Original: {test_text}")
    print(f"  Encoded: {encoded}")
    print(f"  Decoded: {decoded}")
    
    print("\nTesting CharacterTokenizer...")
    char_tokenizer = CharacterTokenizer()
    char_tokenizer.build_vocab(texts)
    
    encoded = char_tokenizer.encode("Hello")
    decoded = char_tokenizer.decode(encoded)
    print(f"  Encoded 'Hello': {encoded}")
    print(f"  Decoded: {decoded}")
    
    print("\n✅ Tokenizer tests passed!")
