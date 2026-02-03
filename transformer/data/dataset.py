"""
Dataset Module
PyTorch datasets for training transformers
"""

import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Optional, Dict, Any, Callable
import random


class TranslationDataset(Dataset):
    """
    Dataset for sequence-to-sequence translation tasks.
    
    Handles parallel source-target text pairs.
    """
    
    def __init__(
        self,
        src_texts: List[str],
        tgt_texts: List[str],
        src_tokenizer,
        tgt_tokenizer,
        max_src_len: int = 128,
        max_tgt_len: int = 128
    ):
        """
        Args:
            src_texts: List of source texts
            tgt_texts: List of target texts
            src_tokenizer: Source tokenizer
            tgt_tokenizer: Target tokenizer
            max_src_len: Maximum source sequence length
            max_tgt_len: Maximum target sequence length
        """
        assert len(src_texts) == len(tgt_texts), "Source and target must have same length"
        
        self.src_texts = src_texts
        self.tgt_texts = tgt_texts
        self.src_tokenizer = src_tokenizer
        self.tgt_tokenizer = tgt_tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len
        
    def __len__(self) -> int:
        return len(self.src_texts)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        src_text = self.src_texts[idx]
        tgt_text = self.tgt_texts[idx]
        
        # Tokenize
        src_ids = self.src_tokenizer.encode(
            src_text,
            max_length=self.max_src_len,
            padding=True
        )
        tgt_ids = self.tgt_tokenizer.encode(
            tgt_text,
            max_length=self.max_tgt_len,
            padding=True
        )
        
        return {
            'src': torch.tensor(src_ids, dtype=torch.long),
            'tgt': torch.tensor(tgt_ids, dtype=torch.long),
        }


class LanguageModelingDataset(Dataset):
    """
    Dataset for language modeling (next token prediction).
    
    Used for decoder-only models like GPT.
    """
    
    def __init__(
        self,
        texts: List[str],
        tokenizer,
        max_length: int = 512,
        stride: int = 256
    ):
        """
        Args:
            texts: List of texts
            tokenizer: Tokenizer
            max_length: Maximum sequence length
            stride: Stride for sliding window (for long texts)
        """
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Tokenize all texts and create chunks
        self.samples = []
        
        for text in texts:
            ids = tokenizer.encode(text, add_special_tokens=False)
            
            # Create overlapping chunks using sliding window
            for i in range(0, len(ids) - max_length + 1, stride):
                chunk = ids[i:i + max_length]
                self.samples.append(chunk)
                
            # Handle last chunk if text is not evenly divisible
            if len(ids) > max_length and len(ids) % stride != 0:
                chunk = ids[-max_length:]
                if chunk not in self.samples:
                    self.samples.append(chunk)
                    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        ids = self.samples[idx]
        
        # Input is all tokens except last
        # Target is all tokens except first (shifted by 1)
        input_ids = torch.tensor(ids[:-1], dtype=torch.long)
        target_ids = torch.tensor(ids[1:], dtype=torch.long)
        
        return {
            'input_ids': input_ids,
            'labels': target_ids,
        }


class TextClassificationDataset(Dataset):
    """
    Dataset for text classification tasks.
    
    Used for encoder-only models like BERT.
    """
    
    def __init__(
        self,
        texts: List[str],
        labels: List[int],
        tokenizer,
        max_length: int = 128
    ):
        """
        Args:
            texts: List of texts
            labels: List of label indices
            tokenizer: Tokenizer
            max_length: Maximum sequence length
        """
        assert len(texts) == len(labels)
        
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self) -> int:
        return len(self.texts)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        label = self.labels[idx]
        
        ids = self.tokenizer.encode(
            text,
            max_length=self.max_length,
            padding=True
        )
        
        return {
            'input_ids': torch.tensor(ids, dtype=torch.long),
            'labels': torch.tensor(label, dtype=torch.long),
        }


def create_translation_dataloaders(
    train_src: List[str],
    train_tgt: List[str],
    val_src: List[str],
    val_tgt: List[str],
    src_tokenizer,
    tgt_tokenizer,
    batch_size: int = 32,
    max_src_len: int = 128,
    max_tgt_len: int = 128,
    num_workers: int = 0
) -> Tuple[DataLoader, DataLoader]:
    """
    Create training and validation DataLoaders for translation.
    
    Args:
        train_src: Training source texts
        train_tgt: Training target texts
        val_src: Validation source texts
        val_tgt: Validation target texts
        src_tokenizer: Source tokenizer
        tgt_tokenizer: Target tokenizer
        batch_size: Batch size
        max_src_len: Maximum source length
        max_tgt_len: Maximum target length
        num_workers: Number of data loading workers
        
    Returns:
        (train_loader, val_loader)
    """
    train_dataset = TranslationDataset(
        train_src, train_tgt,
        src_tokenizer, tgt_tokenizer,
        max_src_len, max_tgt_len
    )
    
    val_dataset = TranslationDataset(
        val_src, val_tgt,
        src_tokenizer, tgt_tokenizer,
        max_src_len, max_tgt_len
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return train_loader, val_loader


class DynamicBatchingDataLoader:
    """
    DataLoader with dynamic batching based on sequence length.
    
    Groups sequences of similar length together to minimize padding
    and improve training efficiency.
    """
    
    def __init__(
        self,
        dataset: Dataset,
        max_tokens: int = 4096,
        shuffle: bool = True
    ):
        """
        Args:
            dataset: Dataset to load from
            max_tokens: Maximum tokens per batch
            shuffle: Shuffle data each epoch
        """
        self.dataset = dataset
        self.max_tokens = max_tokens
        self.shuffle = shuffle
        
    def __iter__(self):
        # Get all samples with their lengths
        indices_and_lengths = []
        for i in range(len(self.dataset)):
            sample = self.dataset[i]
            if 'src' in sample:
                length = sample['src'].ne(0).sum().item()
            else:
                length = sample['input_ids'].ne(0).sum().item()
            indices_and_lengths.append((i, length))
            
        # Sort by length
        indices_and_lengths.sort(key=lambda x: x[1])
        
        # Create batches
        batches = []
        current_batch = []
        current_max_len = 0
        
        for idx, length in indices_and_lengths:
            new_max_len = max(current_max_len, length)
            if len(current_batch) * new_max_len > self.max_tokens:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [idx]
                current_max_len = length
            else:
                current_batch.append(idx)
                current_max_len = new_max_len
                
        if current_batch:
            batches.append(current_batch)
            
        # Shuffle batches
        if self.shuffle:
            random.shuffle(batches)
            
        # Yield batches
        for batch_indices in batches:
            batch = [self.dataset[i] for i in batch_indices]
            yield self._collate(batch)
            
    def _collate(self, batch: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        """Collate batch samples."""
        result = {}
        for key in batch[0].keys():
            tensors = [sample[key] for sample in batch]
            # Pad sequences
            max_len = max(t.size(0) for t in tensors)
            padded = torch.zeros(len(tensors), max_len, dtype=tensors[0].dtype)
            for i, t in enumerate(tensors):
                padded[i, :t.size(0)] = t
            result[key] = padded
        return result
    
    def __len__(self):
        # Approximate number of batches
        total_tokens = sum(
            self.dataset[i].get('src', self.dataset[i].get('input_ids')).ne(0).sum().item()
            for i in range(len(self.dataset))
        )
        return total_tokens // self.max_tokens + 1


if __name__ == "__main__":
    from data.tokenizer import SimpleTokenizer
    
    print("Testing TranslationDataset...")
    
    # Create sample data
    src_texts = [
        "Hello world",
        "How are you",
        "I am fine",
        "Good morning",
    ]
    tgt_texts = [
        "Bonjour monde",
        "Comment allez vous",
        "Je vais bien",
        "Bonjour",
    ]
    
    # Create tokenizers
    src_tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    tgt_tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    src_tokenizer.build_vocab(src_texts)
    tgt_tokenizer.build_vocab(tgt_texts)
    
    # Create dataset
    dataset = TranslationDataset(
        src_texts, tgt_texts,
        src_tokenizer, tgt_tokenizer,
        max_src_len=32, max_tgt_len=32
    )
    
    print(f"  Dataset size: {len(dataset)}")
    sample = dataset[0]
    print(f"  Sample src shape: {sample['src'].shape}")
    print(f"  Sample tgt shape: {sample['tgt'].shape}")
    
    print("\nTesting LanguageModelingDataset...")
    
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a field of artificial intelligence.",
    ]
    
    tokenizer = SimpleTokenizer(vocab_size=1000, min_freq=1)
    tokenizer.build_vocab(texts)
    
    lm_dataset = LanguageModelingDataset(texts, tokenizer, max_length=20, stride=10)
    print(f"  Dataset size: {len(lm_dataset)}")
    sample = lm_dataset[0]
    print(f"  Input shape: {sample['input_ids'].shape}")
    print(f"  Labels shape: {sample['labels'].shape}")
    
    print("\n✅ Dataset tests passed!")
