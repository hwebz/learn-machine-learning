"""
Neural Network Architecture for 2D Diffusion Models.

In DDPM, the model acts as a noise predictor: epsilon_theta(x_t, t).
Given a noisy 2D point x_t and the current timestep integer t, it outputs
an estimate of the noise vector epsilon ~ N(0, I) that was added to x_0.

Key Components:
1. SinusoidalPosEmb: Encodes discrete timesteps t into continuous frequency vectors.
2. ToyMLPDiffusion: Multi-layer perceptron with residual blocks and time-conditioning injection.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class SinusoidalPosEmb(nn.Module):
    """Sinusoidal Positional Embedding for timesteps t.
    
    Transforms a scalar/integer timestep t into a vector of frequencies:
    [sin(t / 10000^(2i/d)), cos(t / 10000^(2i/d))]
    
    This ensures the network can generalize across arbitrary timesteps
    and capture high/low-frequency relationships over time.
    """

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """Args:
            t: Tensor of shape (batch_size,) containing integer or float timesteps
            
        Returns:
            Tensor of shape (batch_size, dim)
        """
        device = t.device
        half_dim = self.dim // 2
        # Frequencies: exp(-log(10000) * i / (half_dim - 1))
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)
        emb = t.unsqueeze(1) * emb.unsqueeze(0)
        emb = torch.cat((torch.sin(emb), torch.cos(emb)), dim=-1)
        return emb


class ResidualBlock(nn.Module):
    """Residual Block with time-embedding conditioning injection."""

    def __init__(self, hidden_dim: int, time_emb_dim: int):
        super().__init__()
        self.time_mlp = nn.Sequential(
            nn.SiLU(),
            nn.Linear(time_emb_dim, hidden_dim)
        )
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.act = nn.SiLU()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
        h = self.fc1(x)
        # Condition injection: add projected time embedding
        h = h + self.time_mlp(t_emb)
        h = self.act(h)
        h = self.fc2(h)
        h = self.norm(h)
        return x + self.act(h)


class ToyMLPDiffusion(nn.Module):
    """Denoising MLP for 2D coordinate diffusion.
    
    Takes noisy coordinates x_t in R^2 and timestep t in [0, T-1],
    and predicts the noise epsilon in R^2.
    """

    def __init__(self, input_dim: int = 2, hidden_dim: int = 128, time_emb_dim: int = 64, num_layers: int = 3):
        super().__init__()
        self.time_embed = nn.Sequential(
            SinusoidalPosEmb(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim),
            nn.SiLU(),
            nn.Linear(time_emb_dim, time_emb_dim),
        )

        self.input_proj = nn.Linear(input_dim, hidden_dim)
        
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim=hidden_dim, time_emb_dim=time_emb_dim)
            for _ in range(num_layers)
        ])
        
        self.output_proj = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, input_dim)
        )

    def forward(self, x_t: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """Args:
            x_t: Noisy coordinate batch of shape (batch_size, 2)
            t: Timesteps batch of shape (batch_size,)
            
        Returns:
            Predicted noise epsilon_theta of shape (batch_size, 2)
        """
        t_emb = self.time_embed(t)
        h = self.input_proj(x_t)
        for block in self.blocks:
            h = block(h, t_emb)
        out = self.output_proj(h)
        return out
