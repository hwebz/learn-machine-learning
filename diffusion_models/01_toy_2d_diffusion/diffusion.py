"""
Denoising Diffusion Probabilistic Models (DDPM) Engine for 2D Distributions.

Implements the fundamental algorithms from:
'Denoising Diffusion Probabilistic Models' (Ho et al., 2020)
https://arxiv.org/abs/2006.11239

Key Math Concepts:
- Forward process q(x_t | x_0): Analytic addition of Gaussian noise.
- Precomputed alpha, beta, and cumulative variance schedules.
- Training loss: MSE between true Gaussian noise and network prediction.
- Reverse sampling loop p_theta(x_{t-1} | x_t): Reconstructing samples from pure noise.
"""

from typing import Tuple, List, Optional
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def linear_beta_schedule(timesteps: int, beta_start: float = 1e-4, beta_end: float = 0.02) -> torch.Tensor:
    """Standard linear beta schedule from Ho et al. 2020."""
    return torch.linspace(beta_start, beta_end, timesteps, dtype=torch.float32)


def cosine_beta_schedule(timesteps: int, s: float = 0.008) -> torch.Tensor:
    """Cosine beta schedule proposed by Nichol & Dhariwal 2021.
    
    Prevents too much noise being added too quickly in early steps.
    """
    steps = timesteps + 1
    x = torch.linspace(0, timesteps, steps, dtype=torch.float32)
    alphas_cumprod = torch.cos(((x / timesteps) + s) / (1 + s) * math.pi * 0.5) ** 2
    alphas_cumprod = alphas_cumprod / alphas_cumprod[0]
    betas = 1 - (alphas_cumprod[1:] / alphas_cumprod[:-1])
    return torch.clip(betas, 0.0001, 0.9999)


class GaussianDiffusion2D:
    """Manages forward noising, loss computation, and reverse sampling for 2D points."""

    def __init__(
        self,
        num_timesteps: int = 100,
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
            raise ValueError(f"Unknown schedule: {beta_schedule}")

        # alpha_t = 1 - beta_t
        self.alphas = 1.0 - self.betas
        # bar{alpha}_t = product_{s=1}^t alpha_s
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        # bar{alpha}_{t-1} with bar{alpha}_0 = 1.0
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)

        # Calculations for forward diffusion q(x_t | x_0)
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)

        # Calculations for reverse process posterior q(x_{t-1} | x_t, x_0)
        self.sqrt_recip_alphas = torch.sqrt(1.0 / self.alphas)
        # Posterior variance: tilde{beta}_t = beta_t * (1 - bar{alpha}_{t-1}) / (1 - bar{alpha}_t)
        self.posterior_variance = (
            self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        )

    def _extract(self, a: torch.Tensor, t: torch.Tensor, x_shape: Tuple[int, ...]) -> torch.Tensor:
        """Extract coefficients at specified timesteps t and reshape for broadcasting."""
        batch_size = t.shape[0]
        out = a.gather(-1, t)
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1)))

    def q_sample(self, x_0: torch.Tensor, t: torch.Tensor, noise: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward diffusion process (Reparameterization Trick).
        
        Directly samples x_t at timestep t without computing steps 1...t-1:
        x_t = sqrt(bar{alpha}_t) * x_0 + sqrt(1 - bar{alpha}_t) * epsilon
        
        Args:
            x_0: Clean data batch of shape (batch_size, 2)
            t: Timestep indices of shape (batch_size,)
            noise: Optional pre-sampled Gaussian noise epsilon ~ N(0, I)
            
        Returns:
            Tuple of (noisy_samples_x_t, ground_truth_noise_epsilon)
        """
        if noise is None:
            noise = torch.randn_like(x_0)

        sqrt_alphas_cumprod_t = self._extract(self.sqrt_alphas_cumprod, t, x_0.shape)
        sqrt_one_minus_alphas_cumprod_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_0.shape)

        x_t = sqrt_alphas_cumprod_t * x_0 + sqrt_one_minus_alphas_cumprod_t * noise
        return x_t, noise

    def compute_loss(self, model: nn.Module, x_0: torch.Tensor) -> torch.Tensor:
        """Computes DDPM training loss (L_simple).
        
        1. Sample random timesteps t uniformly from {0, ..., T-1}.
        2. Sample random Gaussian noise epsilon ~ N(0, I).
        3. Compute noisy samples x_t via q_sample.
        4. Predict noise with model: epsilon_pred = model(x_t, t).
        5. Return MSE loss ||epsilon - epsilon_pred||^2.
        """
        batch_size = x_0.shape[0]
        t = torch.randint(0, self.num_timesteps, (batch_size,), device=self.device).long()
        x_t, noise = self.q_sample(x_0=x_0, t=t)
        
        predicted_noise = model(x_t, t)
        loss = F.mse_loss(predicted_noise, noise)
        return loss

    @torch.no_grad()
    def p_sample(self, model: nn.Module, x_t: torch.Tensor, t_index: int) -> torch.Tensor:
        """Single step of reverse diffusion p_theta(x_{t-1} | x_t).
        
        Uses the model's noise prediction to estimate the mean mu_theta(x_t, t)
        and adds scaled Gaussian noise sigma_t * z (if t > 0).
        """
        batch_size = x_t.shape[0]
        t = torch.full((batch_size,), t_index, device=self.device, dtype=torch.long)

        # 1. Predict noise epsilon_theta(x_t, t)
        predicted_noise = model(x_t, t)

        # 2. Extract schedule constants for timestep t
        beta_t = self._extract(self.betas, t, x_t.shape)
        sqrt_one_minus_alphas_cumprod_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_t.shape)
        sqrt_recip_alphas_t = self._extract(self.sqrt_recip_alphas, t, x_t.shape)

        # 3. Compute predicted mean mu_theta(x_t, t)
        # mu = (1 / sqrt(alpha_t)) * (x_t - (beta_t / sqrt(1 - bar{alpha}_t)) * predicted_noise)
        model_mean = sqrt_recip_alphas_t * (
            x_t - (beta_t / sqrt_one_minus_alphas_cumprod_t) * predicted_noise
        )

        if t_index == 0:
            return model_mean
        else:
            # 4. Add Langevin-like noise: sigma_t * z
            posterior_variance_t = self._extract(self.posterior_variance, t, x_t.shape)
            noise = torch.randn_like(x_t)
            return model_mean + torch.sqrt(posterior_variance_t) * noise

    @torch.no_grad()
    def sample(
        self,
        model: nn.Module,
        shape: Tuple[int, int],
        return_trajectory: bool = False
    ) -> Tuple[torch.Tensor, Optional[List[torch.Tensor]]]:
        """Generates new samples starting from pure isotropic Gaussian noise.
        
        Iterates backwards: t = T-1, T-2, ..., 0.
        
        Args:
            model: Trained denoising network
            shape: (n_samples, 2)
            return_trajectory: If True, returns history of points at all steps
            
        Returns:
            Final denoised samples x_0, and optional list of trajectory tensors
        """
        model.eval()
        # Start at t = T from standard normal distribution
        x = torch.randn(shape, device=self.device)
        trajectory = [x.clone()] if return_trajectory else None

        for t in reversed(range(self.num_timesteps)):
            x = self.p_sample(model, x, t)
            if return_trajectory:
                trajectory.append(x.clone())

        return x, trajectory
