"""
Class-Conditioned Convolutional U-Net with Classifier-Free Guidance (CFG).

Key Extensions over Stage 2:
1. Class Embedding Layer: Embeds integer class labels y in {0, ..., num_classes-1}
   plus an extra Null Token (index num_classes) representing unconditional synthesis.
2. Joint Time-Class Conditioning: Fuses time embedding and label embedding:
   cond = time_mlp(t_emb) + class_mlp(y_emb)
3. Skip Connections & Self-Attention: Preserves spatial edge details and captures
   long-range semantic coherence.
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
    """Residual Block conditioned on joint time-class embeddings."""

    def __init__(self, in_channels: int, out_channels: int, cond_dim: int):
        super().__init__()
        num_groups_in = min(8, in_channels)
        num_groups_out = min(8, out_channels)

        self.norm1 = nn.GroupNorm(num_groups_in, in_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)

        self.cond_proj = nn.Sequential(
            nn.SiLU(),
            nn.Linear(cond_dim, out_channels)
        )

        self.norm2 = nn.GroupNorm(num_groups_out, out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.act = nn.SiLU()

        if in_channels != out_channels:
            self.shortcut = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        h = self.conv1(self.act(self.norm1(x)))
        # Inject combined time + class conditioning
        h = h + self.cond_proj(cond)[:, :, None, None]
        h = self.conv2(self.act(self.norm2(h)))
        return h + self.shortcut(x)


class AttentionBlock(nn.Module):
    """Spatial Multi-Head Self-Attention at bottleneck (7x7)."""

    def __init__(self, channels: int, num_heads: int = 4):
        super().__init__()
        self.norm = nn.GroupNorm(min(8, channels), channels)
        self.mha = nn.MultiheadAttention(embed_dim=channels, num_heads=num_heads, batch_first=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape
        norm_x = self.norm(x)
        flat_x = norm_x.view(b, c, h * w).transpose(1, 2)
        attn_out, _ = self.mha(flat_x, flat_x, flat_x)
        attn_out = attn_out.transpose(1, 2).view(b, c, h, w)
        return x + attn_out


class ConditionalUNet(nn.Module):
    """Class-Conditioned U-Net with CFG Null-Token support for 28x28 images.
    
    Args:
        in_channels: 1 for grayscale
        num_classes: 10 for digits 0-9
        base_channels: 32 base feature maps
        time_emb_dim: 64 embedding dimensions
    """

    def __init__(
        self,
        in_channels: int = 1,
        num_classes: int = 10,
        base_channels: int = 32,
        time_emb_dim: int = 64
    ):
        super().__init__()
        self.num_classes = num_classes
        # Null token index is num_classes (i.e. 10)
        self.null_class = num_classes
        c = base_channels
        cond_dim = time_emb_dim * 2  # 128

        # 1. Timestep Embedding
        self.time_embed = SinusoidalPosEmb(time_emb_dim)
        self.time_mlp = nn.Sequential(
            nn.Linear(time_emb_dim, cond_dim),
            nn.SiLU(),
            nn.Linear(cond_dim, cond_dim)
        )

        # 2. Class Embedding (num_classes + 1 for null token)
        self.class_embed = nn.Embedding(num_classes + 1, time_emb_dim)
        self.class_mlp = nn.Sequential(
            nn.Linear(time_emb_dim, cond_dim),
            nn.SiLU(),
            nn.Linear(cond_dim, cond_dim)
        )

        # 3. Encoder (Downsampling)
        self.init_conv = nn.Conv2d(in_channels, c, kernel_size=3, padding=1)
        self.down1_res = ResBlock(c, c, cond_dim)
        self.down1_conv = nn.Conv2d(c, c * 2, kernel_size=3, stride=2, padding=1)

        self.down2_res = ResBlock(c * 2, c * 2, cond_dim)
        self.down2_conv = nn.Conv2d(c * 2, c * 4, kernel_size=3, stride=2, padding=1)

        # 4. Bottleneck
        self.mid_res1 = ResBlock(c * 4, c * 4, cond_dim)
        self.mid_attn = AttentionBlock(c * 4, num_heads=4)
        self.mid_res2 = ResBlock(c * 4, c * 4, cond_dim)

        # 5. Decoder (Upsampling with Skips)
        self.up1_conv = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=4, stride=2, padding=1)
        self.up1_res = ResBlock(c * 4, c * 2, cond_dim)

        self.up2_conv = nn.ConvTranspose2d(c * 2, c, kernel_size=4, stride=2, padding=1)
        self.up2_res = ResBlock(c * 2, c, cond_dim)

        # 6. Output Projection
        self.final_norm = nn.GroupNorm(min(8, c), c)
        self.final_act = nn.SiLU()
        self.final_conv = nn.Conv2d(c, in_channels, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor, t: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """Args:
            x: Noisy image batch of shape (B, 1, 28, 28)
            t: Integer timesteps batch of shape (B,)
            y: Class labels batch of shape (B,) with values in [0, num_classes]
            
        Returns:
            Predicted noise epsilon_theta of shape (B, 1, 28, 28)
        """
        # Joint conditioning
        t_emb = self.time_mlp(self.time_embed(t))
        y_emb = self.class_mlp(self.class_embed(y))
        cond = t_emb + y_emb

        # Encoder
        x_init = self.init_conv(x)
        d1 = self.down1_res(x_init, cond)
        p1 = self.down1_conv(d1)

        d2 = self.down2_res(p1, cond)
        p2 = self.down2_conv(d2)

        # Bottleneck
        m = self.mid_res1(p2, cond)
        m = self.mid_attn(m)
        m = self.mid_res2(m, cond)

        # Decoder
        u1 = self.up1_conv(m)
        u1 = torch.cat([u1, d2], dim=1)
        u1 = self.up1_res(u1, cond)

        u2 = self.up2_conv(u1)
        u2 = torch.cat([u2, d1], dim=1)
        u2 = self.up2_res(u2, cond)

        return self.final_conv(self.final_act(self.final_norm(u2)))
