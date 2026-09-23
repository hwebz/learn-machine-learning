"""
Convolutional Variational Autoencoder (VAE) for Latent Space Compression.

Compresses high-dimensional images (1 x 28 x 28) by factor f=4 into compact
continuous latent representations (4 x 7 x 7), removing spatial pixel redundancy
and creating the latent manifold for diffusion modeling (the core foundation of Stable Diffusion).
"""

from typing import Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class VAEEncoder(nn.Module):
    """Compresses pixel images (1 x 28 x 28) -> latent parameters (mu, logvar)."""

    def __init__(self, in_channels: int = 1, latent_channels: int = 4, base_channels: int = 32):
        super().__init__()
        # Stage 1: 28x28 -> 14x14
        self.conv1 = nn.Conv2d(in_channels, base_channels, kernel_size=4, stride=2, padding=1)
        self.norm1 = nn.GroupNorm(8, base_channels)
        
        # Stage 2: 14x14 -> 7x7
        self.conv2 = nn.Conv2d(base_channels, base_channels * 2, kernel_size=4, stride=2, padding=1)
        self.norm2 = nn.GroupNorm(8, base_channels * 2)

        # Stage 3: Residual refinement at 7x7
        self.conv3 = nn.Conv2d(base_channels * 2, base_channels * 2, kernel_size=3, padding=1)
        self.norm3 = nn.GroupNorm(8, base_channels * 2)

        # Output mu and logvar (latent_channels * 2)
        self.proj_out = nn.Conv2d(base_channels * 2, latent_channels * 2, kernel_size=1)
        self.act = nn.SiLU()

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.act(self.norm1(self.conv1(x)))
        h = self.act(self.norm2(self.conv2(h)))
        h = self.act(self.norm3(self.conv3(h)))
        params = self.proj_out(h)
        mu, logvar = torch.chunk(params, 2, dim=1)
        return mu, logvar


class VAEDecoder(nn.Module):
    """Reconstructs latent representation (4 x 7 x 7) -> pixel images (1 x 28 x 28)."""

    def __init__(self, latent_channels: int = 4, out_channels: int = 1, base_channels: int = 32):
        super().__init__()
        self.proj_in = nn.Conv2d(latent_channels, base_channels * 2, kernel_size=3, padding=1)

        # Stage 1: 7x7 -> 14x14
        self.up1 = nn.ConvTranspose2d(base_channels * 2, base_channels, kernel_size=4, stride=2, padding=1)
        self.norm1 = nn.GroupNorm(8, base_channels)

        # Stage 2: 14x14 -> 28x28
        self.up2 = nn.ConvTranspose2d(base_channels, base_channels, kernel_size=4, stride=2, padding=1)
        self.norm2 = nn.GroupNorm(8, base_channels)

        # Output projection
        self.conv_out = nn.Conv2d(base_channels, out_channels, kernel_size=3, padding=1)
        self.act = nn.SiLU()

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        h = self.act(self.proj_in(z))
        h = self.act(self.norm1(self.up1(h)))
        h = self.act(self.norm2(self.up2(h)))
        # Output bounded in [-1, 1] using tanh
        out = torch.tanh(self.conv_out(h))
        return out


class AutoencoderKL(nn.Module):
    """Complete Variational Autoencoder with KL-divergence regularized latent space.
    
    In Stable Diffusion, a scaling factor is applied to normalize the latent variance:
    z = z * scale_factor
    """

    def __init__(self, latent_channels: int = 4, base_channels: int = 32, scale_factor: float = 0.5):
        super().__init__()
        self.latent_channels = latent_channels
        self.scale_factor = scale_factor

        self.encoder = VAEEncoder(in_channels=1, latent_channels=latent_channels, base_channels=base_channels)
        self.decoder = VAEDecoder(latent_channels=latent_channels, out_channels=1, base_channels=base_channels)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Sample z ~ N(mu, sigma^2) using reparameterization trick: z = mu + sigma * eps."""
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Encodes images x -> (scaled_z, mu, logvar)."""
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        # Scale latent so standard normal N(0, I) matches its variance
        scaled_z = z * self.scale_factor
        return scaled_z, mu, logvar

    def decode(self, scaled_z: torch.Tensor) -> torch.Tensor:
        """Decodes scaled_z -> reconstructed image x_hat."""
        z = scaled_z / self.scale_factor
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        scaled_z, mu, logvar = self.encode(x)
        x_recon = self.decode(scaled_z)
        return x_recon, mu, logvar

    @staticmethod
    def compute_loss(x: torch.Tensor, x_recon: torch.Tensor, mu: torch.Tensor, logvar: torch.Tensor, kl_weight: float = 1e-4):
        """Computes reconstruction loss (MSE) + KL-divergence loss."""
        recon_loss = F.mse_loss(x_recon, x)
        # KL divergence: -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
        kl_loss = -0.5 * torch.mean(1.0 + logvar - mu.pow(2) - logvar.exp())
        total_loss = recon_loss + kl_weight * kl_loss
        return total_loss, recon_loss, kl_loss
