"""
Denoising Diffusion Implicit Models (DDIM) Sampler.

Implements the non-Markovian fast sampling algorithm from:
'Denoising Diffusion Implicit Models' (Song et al., 2020)
https://arxiv.org/abs/2010.02502

Key Highlights:
1. Arbitrary Step Count: Allows skipping timesteps (e.g. 20 or 50 steps instead of 300).
2. Deterministic Sampling (eta = 0.0): Turns reverse diffusion into an ODE trajectory
   without random noise injection, creating a 1-to-1 bijection between noise and images.
3. Universal Compatibility: Works directly with any trained DDPM checkpoint (unconditional or CFG)
   without requiring retraining!
"""

from typing import Tuple, List, Optional
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def slerp(z0: torch.Tensor, z1: torch.Tensor, alpha: float) -> torch.Tensor:
    """Spherical Linear Interpolation (SLERP) between two Gaussian noise vectors.
    
    Standard linear interpolation z = (1 - alpha) * z0 + alpha * z1 shrinks the norm
    in high dimensions. SLERP rotates along the hypersphere, preserving unit variance.
    """
    z0_norm = z0 / torch.norm(z0, dim=-1, keepdim=True)
    z1_norm = z1 / torch.norm(z1, dim=-1, keepdim=True)
    dot = torch.sum(z0_norm * z1_norm, dim=-1, keepdim=True)
    dot = torch.clamp(dot, -0.9995, 0.9995)

    omega = torch.acos(dot)
    so = torch.sin(omega)
    return (torch.sin((1.0 - alpha) * omega) / so) * z0 + (torch.sin(alpha * omega) / so) * z1


class DDIMSampler:
    """Fast non-Markovian sampler for trained diffusion models."""

    def __init__(
        self,
        num_train_timesteps: int = 300,
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
        device: torch.device = torch.device("cpu")
    ):
        self.num_train_timesteps = num_train_timesteps
        self.device = device

        self.betas = torch.linspace(beta_start, beta_end, num_train_timesteps, dtype=torch.float32, device=device)
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)

    def _get_timesteps(self, num_sampling_steps: int) -> List[int]:
        """Creates an evenly spaced sub-sequence of timesteps from 0 to T-1."""
        step_ratio = self.num_train_timesteps // num_sampling_steps
        timesteps = (np.arange(0, num_sampling_steps) * step_ratio).round().astype(np.int64)
        return timesteps.tolist()

    @torch.no_grad()
    def ddim_step(
        self,
        model: nn.Module,
        x_t: torch.Tensor,
        t: int,
        prev_t: int,
        eta: float = 0.0,
        y: Optional[torch.Tensor] = None,
        guidance_scale: float = 1.0
    ) -> torch.Tensor:
        """Executes a single generalized DDIM update step from timestep t to prev_t.
        
        Args:
            model: Trained U-Net (unconditional or conditional)
            x_t: Current noisy tensor at step t
            t: Current timestep index in [0, T-1]
            prev_t: Next lower timestep index (or -1 if final step)
            eta: Stochasticity coefficient (0.0 = deterministic ODE, 1.0 = stochastic DDPM)
            y: Optional class conditioning tensor
            guidance_scale: CFG scale w
        """
        batch_size = x_t.shape[0]
        t_tensor = torch.full((batch_size,), t, device=self.device, dtype=torch.long)

        # 1. Predict noise epsilon_theta
        if y is not None and hasattr(model, 'null_class') and guidance_scale != 1.0:
            # Batched conditional and unconditional pass for CFG
            x_combined = torch.cat([x_t, x_t], dim=0)
            t_combined = torch.cat([t_tensor, t_tensor], dim=0)
            null_y = torch.full_like(y, model.null_class)
            y_combined = torch.cat([y, null_y], dim=0)

            eps_combined = model(x_combined, t_combined, y_combined)
            eps_cond, eps_uncond = torch.chunk(eps_combined, 2, dim=0)
            eps = eps_uncond + guidance_scale * (eps_cond - eps_uncond)
        elif y is not None:
            eps = model(x_t, t_tensor, y)
        else:
            eps = model(x_t, t_tensor)

        # 2. Extract schedule constants for t and prev_t
        alpha_bar_t = self.alphas_cumprod[t]
        alpha_bar_prev = self.alphas_cumprod[prev_t] if prev_t >= 0 else torch.tensor(1.0, device=self.device)

        # 3. Estimate clean sample hat{x}_0
        pred_x0 = (x_t - torch.sqrt(1.0 - alpha_bar_t) * eps) / torch.sqrt(alpha_bar_t)
        pred_x0 = torch.clamp(pred_x0, -1.0, 1.0)

        # 4. Compute variance sigma_t
        if prev_t < 0 or eta == 0.0:
            sigma_t = 0.0
        else:
            sigma_t = eta * torch.sqrt(
                ((1.0 - alpha_bar_prev) / (1.0 - alpha_bar_t)) * (1.0 - (alpha_bar_t / alpha_bar_prev))
            )

        # 5. Direction pointing to x_t
        dir_xt = torch.sqrt(torch.clamp(1.0 - alpha_bar_prev - sigma_t ** 2, min=0.0)) * eps

        # 6. Compute x_{prev_t}
        x_prev = torch.sqrt(alpha_bar_prev) * pred_x0 + dir_xt
        if sigma_t > 0:
            noise = torch.randn_like(x_t)
            x_prev = x_prev + sigma_t * noise

        return x_prev

    @torch.no_grad()
    def sample(
        self,
        model: nn.Module,
        shape: Tuple[int, ...],
        num_steps: int = 20,
        eta: float = 0.0,
        y: Optional[torch.Tensor] = None,
        guidance_scale: float = 1.0,
        initial_noise: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Fast reverse sampling loop using DDIM.
        
        Args:
            model: Trained U-Net
            shape: (Batch, Channels, Height, Width)
            num_steps: Sub-sequence steps (e.g. 20 or 50)
            eta: 0.0 for deterministic ODE, 1.0 for stochastic DDPM
            y: Optional class labels
            guidance_scale: CFG scale w
            initial_noise: Optional pre-sampled Gaussian noise
        """
        model.eval()
        timesteps = self._get_timesteps(num_steps)

        if initial_noise is not None:
            img = initial_noise.clone().to(self.device)
        else:
            img = torch.randn(shape, device=self.device)

        # Iterate in reverse through the sub-sequence
        for i in reversed(range(len(timesteps))):
            t = timesteps[i]
            prev_t = timesteps[i - 1] if i > 0 else -1
            img = self.ddim_step(
                model=model,
                x_t=img,
                t=t,
                prev_t=prev_t,
                eta=eta,
                y=y,
                guidance_scale=guidance_scale
            )

        return torch.clamp(img, -1.0, 1.0)
