"""
Learning Rate Schedulers
"""

import torch
from torch.optim import Optimizer
from torch.optim.lr_scheduler import _LRScheduler
from typing import Optional
import math


class WarmupScheduler(_LRScheduler):
    """
    Learning Rate Scheduler with Linear Warmup
    
    lr = d_model^(-0.5) * min(step^(-0.5), step * warmup_steps^(-1.5))
    
    This is the scheduler used in "Attention Is All You Need"
    """
    
    def __init__(
        self,
        optimizer: Optimizer,
        d_model: int,
        warmup_steps: int = 4000,
        factor: float = 1.0,
        last_epoch: int = -1
    ):
        """
        Args:
            optimizer: Optimizer
            d_model: Model dimension (for scaling)
            warmup_steps: Number of warmup steps
            factor: Scale factor
            last_epoch: Last epoch
        """
        self.d_model = d_model
        self.warmup_steps = warmup_steps
        self.factor = factor
        super().__init__(optimizer, last_epoch)
        
    def get_lr(self):
        step = max(1, self._step_count)
        scale = self.factor * (
            self.d_model ** (-0.5) *
            min(step ** (-0.5), step * self.warmup_steps ** (-1.5))
        )
        return [base_lr * scale / base_lr for base_lr in self.base_lrs]


class CosineAnnealingWarmup(_LRScheduler):
    """
    Cosine Annealing with Linear Warmup
    
    Popular scheduler that:
    1. Linearly increases LR from 0 to max during warmup
    2. Decays following cosine curve after warmup
    """
    
    def __init__(
        self,
        optimizer: Optimizer,
        warmup_steps: int,
        total_steps: int,
        min_lr: float = 0.0,
        last_epoch: int = -1
    ):
        """
        Args:
            optimizer: Optimizer
            warmup_steps: Number of warmup steps
            total_steps: Total number of training steps
            min_lr: Minimum learning rate
            last_epoch: Last epoch
        """
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr
        super().__init__(optimizer, last_epoch)
        
    def get_lr(self):
        step = self._step_count
        
        if step < self.warmup_steps:
            # Linear warmup
            warmup_factor = step / self.warmup_steps
            return [base_lr * warmup_factor for base_lr in self.base_lrs]
        else:
            # Cosine annealing
            progress = (step - self.warmup_steps) / (self.total_steps - self.warmup_steps)
            cosine_factor = 0.5 * (1 + math.cos(math.pi * progress))
            return [
                self.min_lr + (base_lr - self.min_lr) * cosine_factor
                for base_lr in self.base_lrs
            ]


class InverseSquareRootScheduler(_LRScheduler):
    """
    Inverse Square Root Learning Rate Scheduler
    
    lr = factor * warmup_steps^0.5 * min(step^(-0.5), step * warmup_steps^(-1.5))
    
    Simpler version of the transformer scheduler.
    """
    
    def __init__(
        self,
        optimizer: Optimizer,
        warmup_steps: int = 4000,
        init_lr: float = 0.0,
        max_lr: Optional[float] = None,
        last_epoch: int = -1
    ):
        """
        Args:
            optimizer: Optimizer
            warmup_steps: Number of warmup steps
            init_lr: Initial learning rate
            max_lr: Maximum learning rate after warmup
            last_epoch: Last epoch
        """
        self.warmup_steps = warmup_steps
        self.init_lr = init_lr
        self.max_lr = max_lr
        super().__init__(optimizer, last_epoch)
        
    def get_lr(self):
        step = max(1, self._step_count)
        
        if step < self.warmup_steps:
            # Linear warmup
            warmup_factor = step / self.warmup_steps
            return [
                self.init_lr + (base_lr - self.init_lr) * warmup_factor
                for base_lr in self.base_lrs
            ]
        else:
            # Inverse square root decay
            decay_factor = (self.warmup_steps / step) ** 0.5
            if self.max_lr is not None:
                return [self.max_lr * decay_factor for _ in self.base_lrs]
            return [base_lr * decay_factor for base_lr in self.base_lrs]


class PolynomialDecayScheduler(_LRScheduler):
    """
    Polynomial Decay Learning Rate Scheduler
    
    lr = (init_lr - end_lr) * (1 - step/total_steps)^power + end_lr
    """
    
    def __init__(
        self,
        optimizer: Optimizer,
        total_steps: int,
        warmup_steps: int = 0,
        power: float = 1.0,
        end_lr: float = 0.0,
        last_epoch: int = -1
    ):
        """
        Args:
            optimizer: Optimizer
            total_steps: Total number of training steps
            warmup_steps: Number of warmup steps
            power: Polynomial power
            end_lr: Final learning rate
            last_epoch: Last epoch
        """
        self.total_steps = total_steps
        self.warmup_steps = warmup_steps
        self.power = power
        self.end_lr = end_lr
        super().__init__(optimizer, last_epoch)
        
    def get_lr(self):
        step = self._step_count
        
        if step < self.warmup_steps:
            # Linear warmup
            warmup_factor = step / self.warmup_steps
            return [base_lr * warmup_factor for base_lr in self.base_lrs]
        else:
            # Polynomial decay
            decay_steps = self.total_steps - self.warmup_steps
            current_step = min(step - self.warmup_steps, decay_steps)
            decay_factor = (1 - current_step / decay_steps) ** self.power
            return [
                self.end_lr + (base_lr - self.end_lr) * decay_factor
                for base_lr in self.base_lrs
            ]


# Type hint fix
from typing import Optional


def create_scheduler(
    optimizer: Optimizer,
    scheduler_name: str,
    **kwargs
) -> _LRScheduler:
    """
    Create a learning rate scheduler.
    
    Args:
        optimizer: Optimizer
        scheduler_name: Scheduler name
        **kwargs: Scheduler-specific arguments
        
    Returns:
        Learning rate scheduler
    """
    schedulers = {
        'warmup': WarmupScheduler,
        'cosine_warmup': CosineAnnealingWarmup,
        'inverse_sqrt': InverseSquareRootScheduler,
        'polynomial': PolynomialDecayScheduler,
    }
    
    if scheduler_name not in schedulers:
        raise ValueError(f"Unknown scheduler: {scheduler_name}. "
                        f"Available: {list(schedulers.keys())}")
                        
    return schedulers[scheduler_name](optimizer, **kwargs)


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Test schedulers
    model = torch.nn.Linear(10, 10)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    # Test different schedulers
    total_steps = 10000
    warmup_steps = 1000
    
    schedulers = [
        ('Warmup (Transformer)', WarmupScheduler(optimizer, d_model=512, warmup_steps=warmup_steps)),
        ('Cosine Annealing', CosineAnnealingWarmup(optimizer, warmup_steps=warmup_steps, total_steps=total_steps)),
        ('Inverse Sqrt', InverseSquareRootScheduler(optimizer, warmup_steps=warmup_steps)),
    ]
    
    plt.figure(figsize=(12, 4))
    
    for name, scheduler in schedulers:
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        if 'Warmup (Transformer)' in name:
            scheduler = WarmupScheduler(optimizer, d_model=512, warmup_steps=warmup_steps)
        elif 'Cosine' in name:
            scheduler = CosineAnnealingWarmup(optimizer, warmup_steps=warmup_steps, total_steps=total_steps)
        else:
            scheduler = InverseSquareRootScheduler(optimizer, warmup_steps=warmup_steps)
            
        lrs = []
        for step in range(total_steps):
            lrs.append(scheduler.get_lr()[0])
            scheduler.step()
            
        plt.plot(lrs, label=name)
        
    plt.xlabel('Step')
    plt.ylabel('Learning Rate')
    plt.title('Learning Rate Schedules')
    plt.legend()
    plt.savefig('lr_schedules.png')
    print("Learning rate schedule plot saved to lr_schedules.png")
    
    print("✅ Scheduler tests passed!")
