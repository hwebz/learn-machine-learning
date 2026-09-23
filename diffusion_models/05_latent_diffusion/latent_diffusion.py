"""
Latent Diffusion Pipeline: End-to-End Latent Denoising + VAE Decoding.

Coordinates:
1. Forward noising in continuous latent space: q(z_t | z_0).
2. Fast DDIM reverse sampling on latents (e.g. 20 steps).
3. Decoding final denoised latent z_0 through the VAE decoder D(z_0) to pixel space.
"""

from typing import Tuple, List, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def linear_beta_schedule(timesteps: int, beta_start: float = 1e-4, beta_end: float = 0.02) -> torch.Tensor:
    return torch.linspace(beta_start, beta_end, timesteps, dtype=torch.float32)


class LatentDiffusionPipeline:
    """Manages latent space diffusion and end-to-end VAE generation."""

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

        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)

    def _extract(self, a: torch.Tensor, t: torch.Tensor, x_shape: Tuple[int, ...]) -> torch.Tensor:
        batch_size = t.shape[0]
        out = a.gather(-1, t)
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1)))

    def q_sample(self, z_0: torch.Tensor, t: torch.Tensor, noise: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        if noise is None:
            noise = torch.randn_like(z_0)
        sqrt_alpha_bar = self._extract(self.sqrt_alphas_cumprod, t, z_0.shape)
        sqrt_one_minus_alpha_bar = self._extract(self.sqrt_one_minus_alphas_cumprod, t, z_0.shape)
        z_t = sqrt_alpha_bar * z_0 + sqrt_one_minus_alpha_bar * noise
        return z_t, noise

    def compute_loss(
        self,
        model: nn.Module,
        z_0: torch.Tensor,
        y: torch.Tensor,
        p_uncond: float = 0.15
    ) -> torch.Tensor:
        """Computes MSE loss predicting latent noise epsilon_theta(z_t, t, y)."""
        batch_size = z_0.shape[0]
        t = torch.randint(0, self.num_timesteps, (batch_size,), device=self.device).long()
        z_t, noise = self.q_sample(z_0=z_0, t=t)

        # Label dropout
        mask = torch.rand(batch_size, device=self.device) < p_uncond
        y_masked = y.clone()
        y_masked[mask] = model.null_class

        predicted_noise = model(z_t, t, y_masked)
        return F.mse_loss(predicted_noise, noise)

    def _get_timesteps(self, num_sampling_steps: int) -> List[int]:
        step_ratio = self.num_timesteps // num_sampling_steps
        timesteps = (np.arange(0, num_sampling_steps) * step_ratio).round().astype(np.int64)
        return timesteps.tolist()

    @torch.no_grad()
    def ddim_step(
        self,
        model: nn.Module,
        z_t: torch.Tensor,
        t: int,
        prev_t: int,
        y: torch.Tensor,
        guidance_scale: float = 3.0
    ) -> torch.Tensor:
        batch_size = z_t.shape[0]
        t_tensor = torch.full((batch_size,), t, device=self.device, dtype=torch.long)

        # CFG Batched evaluation
        if guidance_scale != 1.0:
            z_combined = torch.cat([z_t, z_t], dim=0)
            t_combined = torch.cat([t_tensor, t_tensor], dim=0)
            null_y = torch.full_like(y, model.null_class)
            y_combined = torch.cat([y, null_y], dim=0)

            eps_combined = model(z_combined, t_combined, y_combined)
            eps_cond, eps_uncond = torch.chunk(eps_combined, 2, dim=0)
            eps = eps_uncond + guidance_scale * (eps_cond - eps_uncond)
        else:
            eps = model(z_t, t_tensor, y)

        alpha_bar_t = self.alphas_cumprod[t]
        alpha_bar_prev = self.alphas_cumprod[prev_t] if prev_t >= 0 else torch.tensor(1.0, device=self.device)

        # Predicted clean latent hat{z}_0
        pred_z0 = (z_t - torch.sqrt(1.0 - alpha_bar_t) * eps) / torch.sqrt(alpha_bar_t)
        dir_zt = torch.sqrt(torch.clamp(1.0 - alpha_bar_prev, min=0.0)) * eps
        z_prev = torch.sqrt(alpha_bar_prev) * pred_z0 + dir_zt
        return z_prev

    @torch.no_grad()
    def generate_end_to_end(
        self,
        latent_model: nn.Module,
        vae: nn.Module,
        classes: torch.Tensor,
        num_steps: int = 20,
        guidance_scale: float = 3.0,
        initial_noise: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """End-to-End Latent Diffusion Generation.
        
        1. Start from pure Gaussian noise in latent space z_T ~ N(0, I).
        2. Denoise with 20 DDIM steps -> clean latent z_0.
        3. Pass z_0 through VAE decoder D(z_0) -> high-resolution image x_0.
        
        Returns:
            Tuple of (decoded_pixel_images, denoised_latent_tensors)
        """
        latent_model.eval()
        vae.eval()
        n = classes.shape[0]
        classes = classes.to(self.device)

        # 1. Initialize latent noise: (N, 4, 7, 7)
        if initial_noise is not None:
            z = initial_noise.clone().to(self.device)
        else:
            z = torch.randn((n, 4, 7, 7), device=self.device)

        # 2. Reverse Latent DDIM Denoising
        timesteps = self._get_timesteps(num_steps)
        for i in reversed(range(len(timesteps))):
            t = timesteps[i]
            prev_t = timesteps[i - 1] if i > 0 else -1
            z = self.ddim_step(latent_model, z, t, prev_t, classes, guidance_scale=guidance_scale)

        # 3. Decode latents to pixel space via VAE Decoder
        decoded_images = vae.decode(z)
        return torch.clamp(decoded_images, -1.0, 1.0), z
