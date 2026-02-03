"""
Trainer Module
Training loop with checkpointing, logging, and evaluation
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Optimizer
from torch.cuda.amp import GradScaler, autocast
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import time
import json
from tqdm import tqdm


class Trainer:
    """
    Transformer Trainer
    
    Features:
    - Mixed precision training (AMP)
    - Gradient accumulation
    - Learning rate scheduling
    - Checkpointing
    - TensorBoard logging
    - Early stopping
    """
    
    def __init__(
        self,
        model: nn.Module,
        optimizer: Optimizer,
        criterion: nn.Module,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        scheduler: Optional[Any] = None,
        device: str = "cuda",
        checkpoint_dir: str = "./checkpoints",
        log_dir: str = "./logs",
        max_grad_norm: float = 1.0,
        gradient_accumulation_steps: int = 1,
        mixed_precision: bool = True,
        early_stopping_patience: int = 5,
        save_best_only: bool = True
    ):
        """
        Args:
            model: Transformer model
            optimizer: Optimizer
            criterion: Loss function
            train_loader: Training data loader
            val_loader: Validation data loader
            scheduler: Learning rate scheduler
            device: Device to train on
            checkpoint_dir: Directory to save checkpoints
            log_dir: Directory for logs
            max_grad_norm: Maximum gradient norm for clipping
            gradient_accumulation_steps: Number of steps to accumulate gradients
            mixed_precision: Use mixed precision training
            early_stopping_patience: Patience for early stopping
            save_best_only: Only save best model
        """
        self.model = model.to(device)
        self.optimizer = optimizer
        self.criterion = criterion
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.scheduler = scheduler
        self.device = device
        
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_grad_norm = max_grad_norm
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.mixed_precision = mixed_precision and device == "cuda"
        self.early_stopping_patience = early_stopping_patience
        self.save_best_only = save_best_only
        
        # Mixed precision scaler
        self.scaler = GradScaler() if self.mixed_precision else None
        
        # Training state
        self.current_epoch = 0
        self.global_step = 0
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        
        # History
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'learning_rate': [],
        }
        
        # TensorBoard writer
        self.writer = None
        try:
            from torch.utils.tensorboard import SummaryWriter
            self.writer = SummaryWriter(log_dir)
        except ImportError:
            print("TensorBoard not available. Install with: pip install tensorboard")
            
    def train_epoch(self) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        progress_bar = tqdm(
            self.train_loader,
            desc=f"Epoch {self.current_epoch + 1}",
            leave=False
        )
        
        self.optimizer.zero_grad()
        
        for batch_idx, batch in enumerate(progress_bar):
            # Move batch to device
            batch = {k: v.to(self.device) for k, v in batch.items()}
            
            # Forward pass
            with autocast(enabled=self.mixed_precision):
                if 'src' in batch and 'tgt' in batch:
                    # Seq2Seq task
                    src = batch['src']
                    tgt = batch['tgt']
                    # Decoder input is target shifted right
                    tgt_input = tgt[:, :-1]
                    tgt_output = tgt[:, 1:]
                    
                    logits = self.model(src, tgt_input)
                    loss = self.criterion(
                        logits.reshape(-1, logits.size(-1)),
                        tgt_output.reshape(-1)
                    )
                else:
                    # Language modeling task
                    input_ids = batch['input_ids']
                    labels = batch['labels']
                    
                    logits = self.model(input_ids)
                    loss = self.criterion(
                        logits.reshape(-1, logits.size(-1)),
                        labels.reshape(-1)
                    )
                    
                # Scale loss for gradient accumulation
                loss = loss / self.gradient_accumulation_steps
                
            # Backward pass
            if self.mixed_precision:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()
                
            # Update weights
            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                if self.mixed_precision:
                    self.scaler.unscale_(self.optimizer)
                    
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.max_grad_norm
                )
                
                if self.mixed_precision:
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()
                    
                self.optimizer.zero_grad()
                self.global_step += 1
                
                # Update scheduler
                if self.scheduler is not None:
                    self.scheduler.step()
                    
            total_loss += loss.item() * self.gradient_accumulation_steps
            num_batches += 1
            
            # Update progress bar
            progress_bar.set_postfix({
                'loss': f'{loss.item() * self.gradient_accumulation_steps:.4f}',
                'lr': f'{self.get_lr():.2e}'
            })
            
            # Log to TensorBoard
            if self.writer and self.global_step % 100 == 0:
                self.writer.add_scalar('train/loss', loss.item() * self.gradient_accumulation_steps, self.global_step)
                self.writer.add_scalar('train/lr', self.get_lr(), self.global_step)
                
        return total_loss / num_batches
    
    @torch.no_grad()
    def evaluate(self) -> float:
        """Evaluate on validation set."""
        if self.val_loader is None:
            return 0.0
            
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        
        for batch in tqdm(self.val_loader, desc="Evaluating", leave=False):
            batch = {k: v.to(self.device) for k, v in batch.items()}
            
            with autocast(enabled=self.mixed_precision):
                if 'src' in batch and 'tgt' in batch:
                    src = batch['src']
                    tgt = batch['tgt']
                    tgt_input = tgt[:, :-1]
                    tgt_output = tgt[:, 1:]
                    
                    logits = self.model(src, tgt_input)
                    loss = self.criterion(
                        logits.reshape(-1, logits.size(-1)),
                        tgt_output.reshape(-1)
                    )
                else:
                    input_ids = batch['input_ids']
                    labels = batch['labels']
                    
                    logits = self.model(input_ids)
                    loss = self.criterion(
                        logits.reshape(-1, logits.size(-1)),
                        labels.reshape(-1)
                    )
                    
            total_loss += loss.item()
            num_batches += 1
            
        return total_loss / num_batches
    
    def train(self, num_epochs: int, resume_from: Optional[str] = None) -> Dict[str, List[float]]:
        """
        Train the model.
        
        Args:
            num_epochs: Number of epochs to train
            resume_from: Path to checkpoint to resume from
            
        Returns:
            Training history
        """
        # Resume from checkpoint if specified
        if resume_from:
            self.load_checkpoint(resume_from)
            
        print(f"Training on {self.device}")
        print(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        print(f"Trainable parameters: {sum(p.numel() for p in self.model.parameters() if p.requires_grad):,}")
        print()
        
        start_time = time.time()
        
        for epoch in range(self.current_epoch, num_epochs):
            self.current_epoch = epoch
            epoch_start_time = time.time()
            
            # Train
            train_loss = self.train_epoch()
            self.history['train_loss'].append(train_loss)
            self.history['learning_rate'].append(self.get_lr())
            
            # Evaluate
            val_loss = self.evaluate()
            self.history['val_loss'].append(val_loss)
            
            epoch_time = time.time() - epoch_start_time
            
            # Print epoch summary
            print(f"Epoch {epoch + 1}/{num_epochs} | "
                  f"Train Loss: {train_loss:.4f} | "
                  f"Val Loss: {val_loss:.4f} | "
                  f"LR: {self.get_lr():.2e} | "
                  f"Time: {epoch_time:.1f}s")
            
            # Log to TensorBoard
            if self.writer:
                self.writer.add_scalar('epoch/train_loss', train_loss, epoch)
                self.writer.add_scalar('epoch/val_loss', val_loss, epoch)
                
            # Save checkpoint
            is_best = val_loss < self.best_val_loss
            if is_best:
                self.best_val_loss = val_loss
                self.patience_counter = 0
            else:
                self.patience_counter += 1
                
            if not self.save_best_only or is_best:
                self.save_checkpoint(is_best=is_best)
                
            # Early stopping
            if self.patience_counter >= self.early_stopping_patience:
                print(f"Early stopping after {epoch + 1} epochs")
                break
                
        total_time = time.time() - start_time
        print(f"\nTraining completed in {total_time / 60:.1f} minutes")
        print(f"Best validation loss: {self.best_val_loss:.4f}")
        
        # Save training history
        self.save_history()
        
        return self.history
    
    def get_lr(self) -> float:
        """Get current learning rate."""
        return self.optimizer.param_groups[0]['lr']
    
    def save_checkpoint(self, is_best: bool = False) -> None:
        """Save model checkpoint."""
        checkpoint = {
            'epoch': self.current_epoch,
            'global_step': self.global_step,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_val_loss': self.best_val_loss,
            'history': self.history,
        }
        
        if self.scheduler is not None:
            checkpoint['scheduler_state_dict'] = self.scheduler.state_dict()
            
        if self.scaler is not None:
            checkpoint['scaler_state_dict'] = self.scaler.state_dict()
            
        # Save latest checkpoint
        torch.save(checkpoint, self.checkpoint_dir / 'latest.pt')
        
        # Save best checkpoint
        if is_best:
            torch.save(checkpoint, self.checkpoint_dir / 'best.pt')
            
        # Save epoch checkpoint
        if not self.save_best_only:
            torch.save(checkpoint, self.checkpoint_dir / f'epoch_{self.current_epoch + 1}.pt')
            
    def load_checkpoint(self, path: str) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.current_epoch = checkpoint['epoch'] + 1
        self.global_step = checkpoint['global_step']
        self.best_val_loss = checkpoint['best_val_loss']
        self.history = checkpoint['history']
        
        if self.scheduler is not None and 'scheduler_state_dict' in checkpoint:
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            
        if self.scaler is not None and 'scaler_state_dict' in checkpoint:
            self.scaler.load_state_dict(checkpoint['scaler_state_dict'])
            
        print(f"Resumed from epoch {self.current_epoch}")
        
    def save_history(self) -> None:
        """Save training history to file."""
        with open(self.checkpoint_dir / 'history.json', 'w') as f:
            json.dump(self.history, f, indent=2)


def create_optimizer(
    model: nn.Module,
    optimizer_name: str = "adamw",
    lr: float = 1e-4,
    weight_decay: float = 0.01,
    betas: tuple = (0.9, 0.98),
    eps: float = 1e-9
) -> Optimizer:
    """
    Create optimizer with weight decay fix.
    
    Applies weight decay to all parameters except:
    - Bias terms
    - LayerNorm parameters
    
    Args:
        model: Model to optimize
        optimizer_name: Optimizer name ("adam", "adamw", "sgd")
        lr: Learning rate
        weight_decay: Weight decay
        betas: Adam betas
        eps: Adam epsilon
        
    Returns:
        Configured optimizer
    """
    # Separate parameters with/without weight decay
    decay_params = []
    no_decay_params = []
    
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if 'bias' in name or 'norm' in name.lower() or 'ln' in name.lower():
            no_decay_params.append(param)
        else:
            decay_params.append(param)
            
    param_groups = [
        {'params': decay_params, 'weight_decay': weight_decay},
        {'params': no_decay_params, 'weight_decay': 0.0},
    ]
    
    if optimizer_name.lower() == "adam":
        return torch.optim.Adam(param_groups, lr=lr, betas=betas, eps=eps)
    elif optimizer_name.lower() == "adamw":
        return torch.optim.AdamW(param_groups, lr=lr, betas=betas, eps=eps)
    elif optimizer_name.lower() == "sgd":
        return torch.optim.SGD(param_groups, lr=lr, momentum=0.9)
    else:
        raise ValueError(f"Unknown optimizer: {optimizer_name}")


if __name__ == "__main__":
    print("Trainer module loaded successfully!")
    print("Use Trainer class to train transformer models.")
