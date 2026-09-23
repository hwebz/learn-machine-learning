"""
Lightweight Convolutional U-Net for 28x28 Grayscale Vision DDPM.

Key Architectural Elements:
1. SinusoidalPosEmb: Transforms discrete timestep t to continuous frequency vectors.
2. ResBlock: Convolutional residual block conditioned on projected time embeddings.
3. AttentionBlock: Spatial self-attention at the bottleneck (7x7 resolution).
4. Skip Connections: Concatenates encoder feature maps directly into decoder layers,
   preserving high-frequency spatial edge details lost during downsampling.
"""

import math
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


class ResBlock(nn.Module):
    """Residual Block with time-embedding conditioning injection."""

    def __init__(self, in_channels: int, out_channels: int, time_emb_dim: int):
        super().__init__()
        num_groups_in = min(8, in_channels)
        num_groups_out = min(8, out_channels)

        self.norm1 = nn.GroupNorm(num_groups_in, in_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)

        self.time_proj = nn.Sequential(
            nn.SiLU(),
            nn.Linear(time_emb_dim, out_channels)
        )

        self.norm2 = nn.GroupNorm(num_groups_out, out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.act = nn.SiLU()

        if in_channels != out_channels:
            self.shortcut = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
        h = self.conv1(self.act(self.norm1(x)))
        # Inject time embedding: project and broadcast across (H, W)
        h = h + self.time_proj(t_emb)[:, :, None, None]
        h = self.conv2(self.act(self.norm2(h)))
        return h + self.shortcut(x)


class AttentionBlock(nn.Module):
    """Lightweight Multi-Head Self-Attention at the bottleneck (7x7)."""

    def __init__(self, channels: int, num_heads: int = 4):
        super().__init__()
        self.norm = nn.GroupNorm(min(8, channels), channels)
        self.mha = nn.MultiheadAttention(embed_dim=channels, num_heads=num_heads, batch_first=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape
        norm_x = self.norm(x)
        # Reshape to (Batch, Sequence, Channels)
        flat_x = norm_x.view(b, c, h * w).transpose(1, 2)
        attn_out, _ = self.mha(flat_x, flat_x, flat_x)
        attn_out = attn_out.transpose(1, 2).view(b, c, h, w)
        return x + attn_out


class SmallUNet(nn.Module):
    """Compact 2D Convolutional U-Net for 28x28 images.
    
    Total parameters: ~750k
    Input:  (B, in_channels, 28, 28) and (B,) timesteps
    Output: (B, in_channels, 28, 28) predicted noise epsilon
    """

    def __init__(self, in_channels: int = 1, base_channels: int = 32, time_emb_dim: int = 64):
        super().__init__()
        self.time_emb_dim = time_emb_dim
        c = base_channels  # 32

        # 1. Timestep Embedding MLP
        self.time_mlp = nn.Sequential(
            SinusoidalPosEmb(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim * 2),
            nn.SiLU(),
            nn.Linear(time_emb_dim * 2, time_emb_dim * 2)
        )
        t_dim = time_emb_dim * 2  # 128

        # 2. Encoder (Downsampling)
        # 28x28 -> channels c (32)
        self.init_conv = nn.Conv2d(in_channels, c, kernel_size=3, padding=1)
        self.down1_res = ResBlock(c, c, t_dim)
        # Downsample: 28x28 -> 14x14, channels 32 -> 64 (2*c)
        self.down1_conv = nn.Conv2d(c, c * 2, kernel_size=3, stride=2, padding=1)

        # 14x14
        self.down2_res = ResBlock(c * 2, c * 2, t_dim)
        # Downsample: 14x14 -> 7x7, channels 64 -> 128 (4*c)
        self.down2_conv = nn.Conv2d(c * 2, c * 4, kernel_size=3, stride=2, padding=1)

        # 3. Bottleneck (7x7)
        self.mid_res1 = ResBlock(c * 4, c * 4, t_dim)
        self.mid_attn = AttentionBlock(c * 4, num_heads=4)
        self.mid_res2 = ResBlock(c * 4, c * 4, t_dim)

        # 4. Decoder (Upsampling with Skip Connections)
        # Upsample: 7x7 -> 14x14, channels 128 -> 64
        self.up1_conv = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=4, stride=2, padding=1)
        # Concat skip from down2 (c*2 + c*2 = 4*c = 128)
        self.up1_res = ResBlock(c * 4, c * 2, t_dim)

        # Upsample: 14x14 -> 28x28, channels 64 -> 32
        self.up2_conv = nn.ConvTranspose2d(c * 2, c, kernel_size=4, stride=2, padding=1)
        # Concat skip from init_conv/down1 (c + c = 2*c = 64)
        self.up2_res = ResBlock(c * 2, c, t_dim)

        # 5. Output Projection
        self.final_norm = nn.GroupNorm(min(8, c), c)
        self.final_act = nn.SiLU()
        self.final_conv = nn.Conv2d(c, in_channels, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        t_emb = self.time_mlp(t)

        # Encoder
        x_init = self.init_conv(x)          # (B, 32, 28, 28)
        d1 = self.down1_res(x_init, t_emb)  # (B, 32, 28, 28)
        p1 = self.down1_conv(d1)            # (B, 64, 14, 14)

        d2 = self.down2_res(p1, t_emb)      # (B, 64, 14, 14)
        p2 = self.down2_conv(d2)            # (B, 128, 7, 7)

        # Bottleneck
        m = self.mid_res1(p2, t_emb)
        m = self.mid_attn(m)
        m = self.mid_res2(m, t_emb)         # (B, 128, 7, 7)

        # Decoder with Skips
        u1 = self.up1_conv(m)               # (B, 64, 14, 14)
        u1 = torch.cat([u1, d2], dim=1)     # (B, 128, 14, 14)
        u1 = self.up1_res(u1, t_emb)        # (B, 64, 14, 14)

        u2 = self.up2_conv(u1)              # (B, 32, 28, 28)
        u2 = torch.cat([u2, d1], dim=1)     # (B, 64, 28, 28)
        u2 = self.up2_res(u2, t_emb)        # (B, 32, 28, 28)

        # Final projection to epsilon
        out = self.final_conv(self.final_act(self.final_norm(u2)))
        return out
