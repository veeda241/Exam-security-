"""
Loss Functions for Transformer Training
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class LabelSmoothingLoss(nn.Module):
    """
    Label Smoothing Cross-Entropy Loss
    
    Instead of using hard labels (0 or 1), uses soft labels:
    - Target class: (1 - smoothing)
    - Other classes: smoothing / (num_classes - 1)
    
    This helps prevent overconfidence and improves generalization.
    """
    
    def __init__(
        self,
        vocab_size: int,
        smoothing: float = 0.1,
        ignore_index: int = 0
    ):
        """
        Args:
            vocab_size: Vocabulary size
            smoothing: Smoothing factor (0 = no smoothing)
            ignore_index: Index to ignore in loss calculation (e.g., padding)
        """
        super().__init__()
        self.vocab_size = vocab_size
        self.smoothing = smoothing
        self.ignore_index = ignore_index
        self.confidence = 1.0 - smoothing
        
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: Model output logits (batch * seq_len, vocab_size)
            targets: Target token IDs (batch * seq_len,)
            
        Returns:
            Smoothed cross-entropy loss
        """
        # Log softmax for numerical stability
        log_probs = F.log_softmax(logits, dim=-1)
        
        # Create smoothed target distribution
        smooth_targets = torch.zeros_like(log_probs)
        smooth_targets.fill_(self.smoothing / (self.vocab_size - 2))  # -2 for target and ignore
        smooth_targets.scatter_(1, targets.unsqueeze(1), self.confidence)
        
        # Mask for padding tokens
        mask = (targets != self.ignore_index).float().unsqueeze(1)
        
        # Calculate loss
        loss = -torch.sum(smooth_targets * log_probs * mask) / mask.sum()
        
        return loss


class FocalLoss(nn.Module):
    """
    Focal Loss for handling class imbalance.
    
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    
    The modulating factor (1 - p_t)^gamma reduces the loss contribution
    from easy examples and focuses on hard misclassified examples.
    """
    
    def __init__(
        self,
        gamma: float = 2.0,
        alpha: float = 0.25,
        ignore_index: int = 0
    ):
        """
        Args:
            gamma: Focusing parameter (higher = more focus on hard examples)
            alpha: Weighting factor
            ignore_index: Index to ignore
        """
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.ignore_index = ignore_index
        
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: Model output logits (batch * seq_len, vocab_size)
            targets: Target token IDs (batch * seq_len,)
            
        Returns:
            Focal loss
        """
        # Calculate cross-entropy
        ce_loss = F.cross_entropy(
            logits, targets,
            reduction='none',
            ignore_index=self.ignore_index
        )
        
        # Calculate probabilities
        probs = torch.softmax(logits, dim=-1)
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        
        # Focal weight
        focal_weight = (1 - pt) ** self.gamma
        
        # Apply alpha weighting
        loss = self.alpha * focal_weight * ce_loss
        
        # Mask padding
        mask = (targets != self.ignore_index).float()
        loss = (loss * mask).sum() / mask.sum()
        
        return loss


class ContrastiveLoss(nn.Module):
    """
    Contrastive Loss for representation learning.
    
    Used in models like SimCLR for self-supervised learning.
    """
    
    def __init__(self, temperature: float = 0.07):
        """
        Args:
            temperature: Temperature scaling factor
        """
        super().__init__()
        self.temperature = temperature
        
    def forward(
        self,
        z_i: torch.Tensor,
        z_j: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            z_i: First view representations (batch, dim)
            z_j: Second view representations (batch, dim)
            
        Returns:
            Contrastive loss
        """
        batch_size = z_i.size(0)
        
        # Normalize representations
        z_i = F.normalize(z_i, dim=1)
        z_j = F.normalize(z_j, dim=1)
        
        # Concatenate representations
        representations = torch.cat([z_i, z_j], dim=0)  # (2*batch, dim)
        
        # Compute similarity matrix
        similarity = torch.mm(representations, representations.t())  # (2*batch, 2*batch)
        similarity = similarity / self.temperature
        
        # Create labels for contrastive learning
        labels = torch.cat([
            torch.arange(batch_size) + batch_size,  # Positive pairs for z_i are in z_j
            torch.arange(batch_size)  # Positive pairs for z_j are in z_i
        ]).to(z_i.device)
        
        # Remove diagonal (self-similarity)
        mask = ~torch.eye(2 * batch_size, dtype=torch.bool, device=z_i.device)
        similarity = similarity.masked_select(mask).view(2 * batch_size, -1)
        
        # Cross-entropy loss
        loss = F.cross_entropy(similarity, labels)
        
        return loss


class SequenceLoss(nn.Module):
    """
    Standard sequence-to-sequence loss with optional label smoothing.
    
    Wrapper that handles the sequence dimension and ignores padding.
    """
    
    def __init__(
        self,
        vocab_size: int,
        pad_token_id: int = 0,
        label_smoothing: float = 0.0
    ):
        """
        Args:
            vocab_size: Vocabulary size
            pad_token_id: Padding token ID
            label_smoothing: Label smoothing factor
        """
        super().__init__()
        self.vocab_size = vocab_size
        self.pad_token_id = pad_token_id
        
        if label_smoothing > 0:
            self.criterion = LabelSmoothingLoss(
                vocab_size, label_smoothing, pad_token_id
            )
        else:
            self.criterion = nn.CrossEntropyLoss(ignore_index=pad_token_id)
            
    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            logits: Model output (batch, seq_len, vocab_size)
            targets: Target IDs (batch, seq_len)
            
        Returns:
            Loss value
        """
        # Flatten for loss calculation
        logits_flat = logits.view(-1, self.vocab_size)
        targets_flat = targets.view(-1)
        
        return self.criterion(logits_flat, targets_flat)


def compute_perplexity(loss: torch.Tensor) -> torch.Tensor:
    """
    Compute perplexity from cross-entropy loss.
    
    Perplexity = exp(loss)
    
    Args:
        loss: Cross-entropy loss
        
    Returns:
        Perplexity
    """
    return torch.exp(loss)


if __name__ == "__main__":
    print("Testing Label Smoothing Loss...")
    
    vocab_size = 1000
    batch_size = 4
    seq_len = 10
    
    criterion = LabelSmoothingLoss(vocab_size=vocab_size, smoothing=0.1)
    
    logits = torch.randn(batch_size * seq_len, vocab_size)
    targets = torch.randint(1, vocab_size, (batch_size * seq_len,))
    
    loss = criterion(logits, targets)
    print(f"  Loss: {loss.item():.4f}")
    print(f"  Perplexity: {compute_perplexity(loss).item():.2f}")
    
    print("\nTesting Sequence Loss...")
    seq_criterion = SequenceLoss(vocab_size=vocab_size, label_smoothing=0.1)
    
    logits = torch.randn(batch_size, seq_len, vocab_size)
    targets = torch.randint(1, vocab_size, (batch_size, seq_len))
    
    loss = seq_criterion(logits, targets)
    print(f"  Loss: {loss.item():.4f}")
    
    print("\n✅ Loss tests passed!")
