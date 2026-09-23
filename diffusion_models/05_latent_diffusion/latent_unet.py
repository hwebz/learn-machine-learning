"""
Latent Denoising U-Net with Cross-Attention (Stable Diffusion Architecture).

Operates on compressed continuous latent representations z in R^(B x 4 x 7 x 7).

Key Highlights:
1. Spatial Cross-Attention:
   Spatial latent queries Q attend to conditioning tokens K, V (text or class embeddings),
   mirroring the conditioning mechanism of Stable Diffusion and SDXL.
2. Latent Scale:
   Because the spatial resolution is only 7x7, training and inference execute at
   fraction-of-a-second speeds on standard hardware!
"""

import math
from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class SinusoidalPosEmb(nn.Module):
    """Sinusoidal Positional Embedding for timestep t."""

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        device = t.device
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)
        emb = t.unsqueeze(1) * emb.unsqueeze(0)
        return torch.cat((torch.sin(emb), torch.cos(emb)), dim=-1)


class CrossAttentionBlock(nn.Module):
    """Multi-Head Cross-Attention Layer.
    
    Queries (Q): Projected from spatial latent feature maps (B, H*W, channels).
    Keys/Values (K, V): Projected from conditioning token sequence (B, seq_len, context_dim).
    """

    def __init__(self, channels: int, context_dim: int, num_heads: int = 4):
        super().__init__()
        self.channels = channels
        self.num_heads = num_heads
        self.norm = nn.GroupNorm(min(8, channels), channels)

        self.to_q = nn.Linear(channels, channels, bias=False)
        self.to_k = nn.Linear(context_dim, channels, bias=False)
        self.to_v = nn.Linear(context_dim, channels, bias=False)
        self.to_out = nn.Linear(channels, channels)

    def forward(self, x: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        """Args:
            x: Latent feature map of shape (B, C, H, W)
            context: Conditioning token sequence of shape (B, seq_len, context_dim)
        """
        b, c, h, w = x.shape
        norm_x = self.norm(x)
        q = norm_x.view(b, c, h * w).transpose(1, 2)  # (B, H*W, C)
        q = self.to_q(q)

        k = self.to_k(context)  # (B, seq_len, C)
        v = self.to_v(context)  # (B, seq_len, C)

        # Reshape for multi-head attention
        head_dim = c // self.num_heads
        q = q.view(b, -1, self.num_heads, head_dim).transpose(1, 2)  # (B, heads, H*W, head_dim)
        k = k.view(b, -1, self.num_heads, head_dim).transpose(1, 2)  # (B, heads, seq_len, head_dim)
        v = v.view(b, -1, self.num_heads, head_dim).transpose(1, 2)  # (B, heads, seq_len, head_dim)

        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(head_dim)
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, v)  # (B, heads, H*W, head_dim)

        out = out.transpose(1, 2).contiguous().view(b, -1, c)  # (B, H*W, C)
        out = self.to_out(out).transpose(1, 2).view(b, c, h, w)  # (B, C, H, W)
        return x + out


class LatentResBlock(nn.Module):
    """Residual Block conditioned on projected timestep embeddings."""

    def __init__(self, in_channels: int, out_channels: int, time_emb_dim: int):
        super().__init__()
        self.norm1 = nn.GroupNorm(min(8, in_channels), in_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)

        self.time_proj = nn.Sequential(
            nn.SiLU(),
            nn.Linear(time_emb_dim, out_channels)
        )

        self.norm2 = nn.GroupNorm(min(8, out_channels), out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.act = nn.SiLU()

        if in_channels != out_channels:
            self.shortcut = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
        h = self.conv1(self.act(self.norm1(x)))
        h = h + self.time_proj(t_emb)[:, :, None, None]
        h = self.conv2(self.act(self.norm2(h)))
        return h + self.shortcut(x)


class LatentUNet(nn.Module):
    """Denoising U-Net with Cross-Attention operating in latent space (4 x 7 x 7)."""

    def __init__(
        self,
        latent_channels: int = 4,
        base_channels: int = 64,
        time_emb_dim: int = 64,
        context_dim: int = 64,
        num_classes: int = 10
    ):
        super().__init__()
        self.latent_channels = latent_channels
        self.num_classes = num_classes
        self.null_class = num_classes
        c = base_channels
        t_dim = time_emb_dim * 2

        # 1. Time Embeddings
        self.time_embed = SinusoidalPosEmb(time_emb_dim)
        self.time_mlp = nn.Sequential(
            nn.Linear(time_emb_dim, t_dim),
            nn.SiLU(),
            nn.Linear(t_dim, t_dim)
        )

        # 2. Conditioning Token Projection (Class Embeddings -> Context Sequence)
        self.class_embed = nn.Embedding(num_classes + 1, context_dim)

        # 3. Encoder (7x7)
        self.init_conv = nn.Conv2d(latent_channels, c, kernel_size=3, padding=1)
        self.res1 = LatentResBlock(c, c, t_dim)
        self.cross_attn1 = CrossAttentionBlock(c, context_dim=context_dim)

        # Downsample: 7x7 -> 4x4
        self.down = nn.Conv2d(c, c * 2, kernel_size=3, stride=2, padding=1)
        self.res2 = LatentResBlock(c * 2, c * 2, t_dim)
        self.cross_attn2 = CrossAttentionBlock(c * 2, context_dim=context_dim)

        # 4. Bottleneck (4x4)
        self.mid_res1 = LatentResBlock(c * 2, c * 2, t_dim)
        self.mid_attn = CrossAttentionBlock(c * 2, context_dim=context_dim)
        self.mid_res2 = LatentResBlock(c * 2, c * 2, t_dim)

        # 5. Decoder (4x4 -> 7x7)
        self.up_conv = nn.Conv2d(c * 2, c, kernel_size=3, padding=1)
        self.up_res = LatentResBlock(c * 2, c, t_dim)  # Concat skip from res1
        self.up_cross_attn = CrossAttentionBlock(c, context_dim=context_dim)

        # 6. Output Projection to latent noise
        self.final_norm = nn.GroupNorm(8, c)
        self.final_act = nn.SiLU()
        self.final_conv = nn.Conv2d(c, latent_channels, kernel_size=3, padding=1)

    def forward(self, z_t: torch.Tensor, t: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """Args:
            z_t: Noisy latent tensor of shape (B, 4, 7, 7)
            t: Timestep integers of shape (B,)
            y: Class labels of shape (B,)
            
        Returns:
            Predicted latent noise epsilon of shape (B, 4, 7, 7)
        """
        t_emb = self.time_mlp(self.time_embed(t))
        # Form conditioning token sequence: (B, 1, context_dim)
        context = self.class_embed(y).unsqueeze(1)

        # Encoder
        x0 = self.init_conv(z_t)
        h1 = self.res1(x0, t_emb)
        h1 = self.cross_attn1(h1, context)

        d = self.down(h1)
        h2 = self.res2(d, t_emb)
        h2 = self.cross_attn2(h2, context)

        # Bottleneck
        m = self.mid_res1(h2, t_emb)
        m = self.mid_attn(m, context)
        m = self.mid_res2(m, t_emb)

        # Decoder with Skip
        u = F.interpolate(m, size=h1.shape[-2:], mode='nearest')
        u = self.up_conv(u)
        u = torch.cat([u, h1], dim=1)
        u = self.up_res(u, t_emb)
        u = self.up_cross_attn(u, context)

        return self.final_conv(self.final_act(self.final_norm(u)))
