# Stage 5: Latent Diffusion Models (LDM / Stable Diffusion Architecture)

Welcome to Stage 5! Here we implement **Latent Diffusion Models (LDM)** (Rombach et al., CVPR 2022) — the architecture that powers **Stable Diffusion, SDXL, and Flux**.

---

## 🏗️ The Problem with Pixel-Space Diffusion

In Stages 2 and 3, our diffusion models operated directly on raw image pixels ($x \in \mathbb{R}^{H \times W \times C}$).
While effective, pixel-space diffusion has major limitations at scale:
1. **Computational Inefficiency**: 90% of model capacity is spent predicting imperceptible high-frequency pixel noise rather than global semantics.
2. **Quadratic Scaling**: Generating $512 \times 512$ or $1024 \times 1024$ images directly with conv layers requires massive GPU clusters.

---

## 💡 The Solution: Two-Stage Generative Modeling

Latent Diffusion decouples generative modeling into two distinct components:

```
[Pixel Space]                  [Latent Space]                  [Pixel Space]
    x_0         ─── VAE Encoder ───>  z_0                         x_recon
(1 x 28 x 28)                     (4 x 7 x 7)                 (1 x 28 x 28)
                                       │                            ▲
                                 Add Noise z_t                      │
                                       ▼                            │
                                [Latent U-Net] ── Cross-Attn ─── VAE Decoder
                                       │          Conditioning
                                 Denoised z_0 ──────────────────────┘
```

### 1. Perceptual Compression (VAE)
- Pre-trained and **frozen**.
- Compresses pixels by factor $f=4$ into a compact, continuous latent representation $z \in \mathbb{R}^{4 \times 7 \times 7}$.
- Removes imperceptible pixel noise while preserving semantic geometry.

### 2. Latent Denoising with Cross-Attention
- The diffusion model operates **entirely in the 4×7×7 latent space**!
- Conditioning tokens (class labels or text embeddings) are injected via **Multi-Head Cross-Attention**:
  $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$
  where Queries $Q$ are projected from spatial latent features $(H \cdot W \times C)$, and Keys $K$ & Values $V$ are projected from the conditioning sequence.

---

## 🏃 Hands-On Execution Guide

### Step 1: Train the VAE Compression Autoencoder
```powershell
cd diffusion_models/05_latent_diffusion

# Train VAE for 4 epochs (~20 seconds)
..\.venv\Scripts\python.exe train_vae.py --epochs 4
```
- Checkpoint saved to `checkpoints/vae.pt`.
- Loss curve saved to `outputs/loss_curve_vae.png`.

### Step 2: Visually Inspect VAE Compression & Reconstruction
Verify that the 4 latent channels ($7\times 7$) capture the digit shape:
```powershell
..\.venv\Scripts\python.exe inspect_compression.py
```
*Output image:* `outputs/vae_compression_inspection.png`

### Step 3: Train the Latent Denoising U-Net
```powershell
# Train the Latent U-Net on pre-encoded 4x7x7 latents for 5 epochs (~25 seconds)
..\.venv\Scripts\python.exe train_ldm.py --epochs 5
```
- Checkpoint saved to `checkpoints/latent_unet.pt`.
- Loss curve saved to `outputs/loss_curve_ldm.png`.

### Step 4: End-to-End Latent Diffusion Generation
```powershell
# Denoises latents with 20 DDIM steps and decodes to pixels via VAE
..\.venv\Scripts\python.exe sample_ldm.py --steps 20 --guidance_scale 3.0
```
*Outputs generated:*
1. `outputs/ldm_generated_digits.png`: 10-class showcase grid of synthetic digits generated via latent diffusion.
2. `outputs/ldm_latent_to_pixel.png`: Side-by-side view showing the 4 denoised latent channels directly next to their decoded pixel image!
