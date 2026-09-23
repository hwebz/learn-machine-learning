"""
Classifier-Free Guidance (CFG) Diffusion Engine for Conditional Vision DDPM.

Implements:
1. Training with random label dropout (p_uncond = 0.15) to teach the network
   both conditional p(x|y) and unconditional p(x) distributions simultaneously.
2. Reverse sampling with CFG noise extrapolation:
   eps_tilde = eps_uncond + w * (eps_cond - eps_uncond)
"""

from typing import Tuple, List, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


def linear_beta_schedule(timesteps: int, beta_start: float = 1e-4, beta_end: float = 0.02) -> torch.Tensor:
    return torch.linspace(beta_start, beta_end, timesteps, dtype=torch.float32)


class GaussianDiffusionCFG:
    """Manages forward noising, conditional loss with label dropout, and CFG reverse sampling."""

    def __init__(
        self,
        num_timesteps: int = 300,
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
        device: torch.device = torch.device("cpu")
    ):
        self.num_timesteps = num_timesteps
        self.device = device

        self.betas = linear_beta_schedule(num_timesteps, beta_start, beta_end).to(device)
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)

        # Precomputed constants
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)
        self.sqrt_recip_alphas = torch.sqrt(1.0 / self.alphas)
        self.posterior_variance = (
            self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        )

    def _extract(self, a: torch.Tensor, t: torch.Tensor, x_shape: Tuple[int, ...]) -> torch.Tensor:
        batch_size = t.shape[0]
        out = a.gather(-1, t)
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1)))

    def q_sample(
        self,
        x_0: torch.Tensor,
        t: torch.Tensor,
        noise: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if noise is None:
            noise = torch.randn_like(x_0)

        sqrt_alpha_bar = self._extract(self.sqrt_alphas_cumprod, t, x_0.shape)
        sqrt_one_minus_alpha_bar = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_0.shape)
        x_t = sqrt_alpha_bar * x_0 + sqrt_one_minus_alpha_bar * noise
        return x_t, noise

    def compute_loss(
        self,
        model: nn.Module,
        x_0: torch.Tensor,
        y: torch.Tensor,
        p_uncond: float = 0.15
    ) -> torch.Tensor:
        """Computes conditional DDPM training loss with label dropout.
        
        Args:
            model: ConditionalUNet
            x_0: Ground truth images (B, 1, 28, 28)
            y: Ground truth class labels (B,)
            p_uncond: Probability of dropping label to null token (class 10)
        """
        batch_size = x_0.shape[0]
        t = torch.randint(0, self.num_timesteps, (batch_size,), device=self.device).long()
        x_t, noise = self.q_sample(x_0=x_0, t=t)

        # Randomly mask labels to null class
        mask = torch.rand(batch_size, device=self.device) < p_uncond
        y_masked = y.clone()
        y_masked[mask] = model.null_class

        predicted_noise = model(x_t, t, y_masked)
        return F.mse_loss(predicted_noise, noise)

    @torch.no_grad()
    def p_sample_cfg(
        self,
        model: nn.Module,
        x_t: torch.Tensor,
        t_index: int,
        y: torch.Tensor,
        guidance_scale: float = 3.0
    ) -> torch.Tensor:
        """Single reverse step with Classifier-Free Guidance noise extrapolation.
        
        eps_tilde = eps_uncond + w * (eps_cond - eps_uncond)
        """
        batch_size = x_t.shape[0]
        t = torch.full((batch_size,), t_index, device=self.device, dtype=torch.long)

        if guidance_scale == 0.0:
            # Pure unconditional
            null_y = torch.full_like(y, model.null_class)
            eps_tilde = model(x_t, t, null_y)
        elif guidance_scale == 1.0:
            # Standard conditional without guidance extrapolation
            eps_tilde = model(x_t, t, y)
        else:
            # Batched pass for both conditional and unconditional branches
            x_combined = torch.cat([x_t, x_t], dim=0)
            t_combined = torch.cat([t, t], dim=0)
            null_y = torch.full_like(y, model.null_class)
            y_combined = torch.cat([y, null_y], dim=0)

            eps_combined = model(x_combined, t_combined, y_combined)
            eps_cond, eps_uncond = torch.chunk(eps_combined, 2, dim=0)

            # CFG Extrapolation Formula
            eps_tilde = eps_uncond + guidance_scale * (eps_cond - eps_uncond)

        # Standard DDPM mean and variance update
        beta_t = self._extract(self.betas, t, x_t.shape)
        sqrt_one_minus_alpha_bar_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_t.shape)
        sqrt_recip_alphas_t = self._extract(self.sqrt_recip_alphas, t, x_t.shape)

        model_mean = sqrt_recip_alphas_t * (
            x_t - (beta_t / sqrt_one_minus_alpha_bar_t) * eps_tilde
        )

        if t_index == 0:
            return model_mean
        else:
            posterior_var_t = self._extract(self.posterior_variance, t, x_t.shape)
            noise = torch.randn_like(x_t)
            return model_mean + torch.sqrt(posterior_var_t) * noise

    @torch.no_grad()
    def sample_classes(
        self,
        model: nn.Module,
        classes: torch.Tensor,
        guidance_scale: float = 3.0,
        fixed_noise: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Generates images conditioned on specified class tensor.
        
        Args:
            model: Trained ConditionalUNet
            classes: Tensor of target digit integers, shape (N,)
            guidance_scale: Strength of CFG (w >= 1.0)
            fixed_noise: Optional initial noise seed
            
        Returns:
            Generated images of shape (N, 1, 28, 28) clamped to [-1, 1]
        """
        model.eval()
        n = classes.shape[0]
        classes = classes.to(self.device)

        if fixed_noise is not None:
            img = fixed_noise.clone().to(self.device)
        else:
            img = torch.randn((n, 1, 28, 28), device=self.device)

        for t in reversed(range(self.num_timesteps)):
            img = self.p_sample_cfg(model, img, t, classes, guidance_scale=guidance_scale)

        return torch.clamp(img, -1.0, 1.0)
