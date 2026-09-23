"""
Image DDPM Diffusion Engine for 4D Tensors (Batch, Channels, Height, Width).

Implements:
1. Linear & Cosine variance schedules.
2. Analytic forward noising q(x_t | x_0) with 4D broadcasting.
3. Simple MSE loss L_simple = E[||epsilon - epsilon_theta(x_t, t)||^2].
4. Reverse sampling loop p_theta(x_{t-1} | x_t) generating clean images from pure noise.
"""

from typing import Tuple, List, Optional
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def linear_beta_schedule(timesteps: int, beta_start: float = 1e-4, beta_end: float = 0.02) -> torch.Tensor:
    """Linear beta schedule (Ho et al., 2020)."""
    return torch.linspace(beta_start, beta_end, timesteps, dtype=torch.float32)


def cosine_beta_schedule(timesteps: int, s: float = 0.008) -> torch.Tensor:
    """Cosine beta schedule (Nichol & Dhariwal, 2021)."""
    steps = timesteps + 1
    x = torch.linspace(0, timesteps, steps, dtype=torch.float32)
    alphas_cumprod = torch.cos(((x / timesteps) + s) / (1 + s) * math.pi * 0.5) ** 2
    alphas_cumprod = alphas_cumprod / alphas_cumprod[0]
    betas = 1 - (alphas_cumprod[1:] / alphas_cumprod[:-1])
    return torch.clip(betas, 0.0001, 0.9999)


class GaussianDiffusionImage:
    """Manages forward noising and reverse generation for 4D image tensors."""

    def __init__(
        self,
        num_timesteps: int = 300,
        beta_schedule: str = "linear",
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
        device: torch.device = torch.device("cpu")
    ):
        self.num_timesteps = num_timesteps
        self.device = device

        if beta_schedule == "linear":
            self.betas = linear_beta_schedule(num_timesteps, beta_start, beta_end).to(device)
        elif beta_schedule == "cosine":
            self.betas = cosine_beta_schedule(num_timesteps).to(device)
        else:
            raise ValueError(f"Unknown beta schedule: {beta_schedule}")

        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)

        # Forward process coefficients
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)

        # Reverse process coefficients
        self.sqrt_recip_alphas = torch.sqrt(1.0 / self.alphas)
        self.posterior_variance = (
            self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        )

    def _extract(self, a: torch.Tensor, t: torch.Tensor, x_shape: Tuple[int, ...]) -> torch.Tensor:
        """Extract coefficients at timesteps t and reshape for 4D broadcasting (B, 1, 1, 1)."""
        batch_size = t.shape[0]
        out = a.gather(-1, t)
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1)))

    def q_sample(
        self,
        x_0: torch.Tensor,
        t: torch.Tensor,
        noise: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Closed-form forward diffusion:
        x_t = sqrt(bar{alpha}_t) * x_0 + sqrt(1 - bar{alpha}_t) * epsilon
        """
        if noise is None:
            noise = torch.randn_like(x_0)

        sqrt_alpha_bar = self._extract(self.sqrt_alphas_cumprod, t, x_0.shape)
        sqrt_one_minus_alpha_bar = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_0.shape)

        x_t = sqrt_alpha_bar * x_0 + sqrt_one_minus_alpha_bar * noise
        return x_t, noise

    def compute_loss(self, model: nn.Module, x_0: torch.Tensor) -> torch.Tensor:
        """Computes training loss L_simple = MSE(epsilon, model(x_t, t))."""
        batch_size = x_0.shape[0]
        t = torch.randint(0, self.num_timesteps, (batch_size,), device=self.device).long()
        x_t, noise = self.q_sample(x_0=x_0, t=t)

        predicted_noise = model(x_t, t)
        return F.mse_loss(predicted_noise, noise)

    @torch.no_grad()
    def p_sample(self, model: nn.Module, x_t: torch.Tensor, t_index: int) -> torch.Tensor:
        """Single reverse denoising step p_theta(x_{t-1} | x_t)."""
        batch_size = x_t.shape[0]
        t = torch.full((batch_size,), t_index, device=self.device, dtype=torch.long)

        # 1. Predict noise added at step t
        predicted_noise = model(x_t, t)

        # 2. Extract schedule constants
        beta_t = self._extract(self.betas, t, x_t.shape)
        sqrt_one_minus_alpha_bar_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_t.shape)
        sqrt_recip_alphas_t = self._extract(self.sqrt_recip_alphas, t, x_t.shape)

        # 3. Model predicted mean
        model_mean = sqrt_recip_alphas_t * (
            x_t - (beta_t / sqrt_one_minus_alpha_bar_t) * predicted_noise
        )

        if t_index == 0:
            return model_mean
        else:
            posterior_var_t = self._extract(self.posterior_variance, t, x_t.shape)
            noise = torch.randn_like(x_t)
            return model_mean + torch.sqrt(posterior_var_t) * noise

    @torch.no_grad()
    def sample(
        self,
        model: nn.Module,
        shape: Tuple[int, int, int, int],
        return_trajectory: bool = False
    ) -> Tuple[torch.Tensor, Optional[List[torch.Tensor]]]:
        """Generates novel images from pure Gaussian noise.
        
        Args:
            model: Trained U-Net
            shape: (Batch, Channels, Height, Width), e.g. (16, 1, 28, 28)
            return_trajectory: Whether to store intermediate frames
            
        Returns:
            Final images tensor clamped to [-1, 1], and optional list of intermediate states
        """
        model.eval()
        img = torch.randn(shape, device=self.device)
        trajectory = [img.clone()] if return_trajectory else None

        for t in reversed(range(self.num_timesteps)):
            img = self.p_sample(model, img, t)
            if return_trajectory:
                trajectory.append(img.clone())

        return torch.clamp(img, -1.0, 1.0), trajectory
