# Stage 2: Vision DDPM on 28×28 Grayscale Images (MNIST)

Welcome to Stage 2! In this module, we step up from 2D coordinates into **2D Image Pixels**: generating continuous $28 \times 28$ handwritten digits ($x \in \mathbb{R}^{1 \times 28 \times 28}$) from pure random Gaussian noise.

---

## 🏗️ The Convolutional U-Net Architecture

In Stage 1, we used an MLP because 2D points had no spatial structure. In images, neighboring pixels are strongly correlated. We use a **2D Convolutional U-Net** with residual blocks and skip connections:

```
Input: x_t (B, 1, 28, 28) + Timestep t (B,)
   │
   ▼
[Initial Conv2d] ──> (B, 32, 28, 28) ───────────────────────┐ [Skip Connection 2]
   │                                                         │
   ▼                                                         │
[ResBlock + Downsample Conv] ──> (B, 64, 14, 14) ───┐        │
   │                                                │        │
   ▼                                                │        │
[ResBlock + Downsample Conv] ──> (B, 128, 7, 7)     │        │
   │                                                │ [Skip 1│
   ▼                                                │        │
[Bottleneck: ResBlock + Self-Attention + ResBlock]  │        │
   │                                                │        │
   ▼                                                │        │
[Upsample ConvTranspose] ──> (B, 64, 14, 14)        │        │
   │                                                │        │
   ├── Concat Skip 1 <──────────────────────────────┘        │
   ▼                                                         │
[ResBlock]                                                   │
   │                                                         │
   ▼                                                         │
[Upsample ConvTranspose] ──> (B, 32, 28, 28)                 │
   │                                                         │
   ├── Concat Skip 2 <───────────────────────────────────────┘
   ▼
[ResBlock + GroupNorm + Output Conv]
   │
   ▼
Output: Predicted Noise epsilon_theta (B, 1, 28, 28)
```

### Why Skip Connections Are Critical:
During downsampling ($28\times 28 \to 14\times 14 \to 7\times 7$), high-frequency spatial edge details (stroke sharpness, subtle loops in digits) are lost. Skip connections bypass the bottleneck, feeding fine-grained spatial features directly to corresponding decoder stages!

---

## 🏃 Hands-On Execution Guide

### Step 1: Forward Noise Inspection (No Model Training)
Observe how clean MNIST digits dissolve into static over $T=300$ steps:
```powershell
cd diffusion_models/02_mnist_ddpm
..\.venv\Scripts\python.exe inspect_forward.py --dataset mnist
```
*Output image:* `outputs/forward_diffusion_mnist.png`

### Step 2: Train the Vision U-Net
```powershell
# Standard training (10 epochs on full dataset)
..\.venv\Scripts\python.exe train.py --dataset mnist --epochs 10 --batch_size 128

# Fast preview mode (subset of 5,000 samples for rapid validation)
..\.venv\Scripts\python.exe train.py --dataset mnist --epochs 5 --max_samples 5000
```
- Checkpoint saved to `checkpoints/mnist_ddpm_mnist.pt`.
- Loss curve saved to `outputs/loss_curve_mnist.png`.

### Step 3: Sample Novel Digits
```powershell
..\.venv\Scripts\python.exe sample.py --checkpoint checkpoints/mnist_ddpm_mnist.pt --samples 32
```
Outputs generated:
1. `outputs/generated_digits_mnist.png`: A showcase grid of 32 completely new digits generated from pure noise.
2. `outputs/reverse_denoising_mnist.png`: A step-by-step strip showing digits crystallizing out of static noise.
