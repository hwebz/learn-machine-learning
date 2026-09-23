# Stage 3: Conditional Diffusion & Classifier-Free Guidance (CFG)

Welcome to Stage 3! Here we implement **Classifier-Free Guidance (CFG)** (Ho & Salimans, 2021), the steerability technique used across the generative AI industry (Stable Diffusion, Midjourney, Imagen, DALL-E 3).

---

## 🧠 The Mathematics of Classifier-Free Guidance

In standard conditional generation, a model learns the score $\nabla_{x_t} \log p(x_t | y)$. 
By Bayes' rule:
$$\nabla_{x_t} \log p(x_t | y) = \nabla_{x_t} \log p(x_t) + \nabla_{x_t} \log p(y | x_t)$$

Instead of training a noisy external classifier $p(y | x_t)$, **Classifier-Free Guidance** computes this implicit gradient using a single network!

### 1. Joint Training via Label Dropout
- We train our conditional U-Net $\epsilon_\theta(x_t, t, y)$ on both conditional and unconditional generation.
- With probability $p_{\text{uncond}} = 0.15$, the class label $y$ is randomly replaced by a **Null Token** $\varnothing$ (class index 10).
- When conditioned on $\varnothing$, the network predicts unconditional noise $\epsilon_\theta(x_t, t, \varnothing)$.
- When conditioned on $y$, the network predicts class-specific noise $\epsilon_\theta(x_t, t, y)$.

### 2. Extrapolation during Sampling
During reverse denoising, we evaluate both predictions and extrapolate:
$$\tilde{\epsilon}_\theta(x_t, t, y) = \epsilon_\theta(x_t, t, \varnothing) + w \cdot \Big(\epsilon_\theta(x_t, t, y) - \epsilon_\theta(x_t, t, \varnothing)\Big)$$

- **$w = 0.0$**: Ignores class prompt; outputs random, generic digits.
- **$w = 1.0$**: Standard conditional generation without guidance boost.
- **$w \in [2.0, 4.0]$**: Optimal sweet spot — sharp strokes, high fidelity, perfectly matched to the prompted digit.
- **$w > 7.0$**: High guidance — over-emphasizes class features with hyper-saturated contrast.

---

## 🏃 Hands-On Execution Guide

### Step 1: Train the Conditional U-Net
```powershell
cd diffusion_models/03_conditional_cfg

# Train on 6,400 MNIST samples with 15% label dropout
..\.venv\Scripts\python.exe train.py --dataset mnist --epochs 6 --max_samples 6400
```
- Model checkpoint saved to `checkpoints/mnist_cfg_ddpm_mnist.pt`.
- Loss curve saved to `outputs/loss_curve_cfg_mnist.png`.

### Step 2: Generate Controllable Digit Grids
```powershell
# Generates a 10x6 matrix where row i corresponds to digit i
..\.venv\Scripts\python.exe sample.py --checkpoint checkpoints/mnist_cfg_ddpm_mnist.pt --guidance_scale 3.0
```
*Outputs generated:*
1. `outputs/conditional_digits_mnist.png`: Ordered matrix showing guaranteed class generation for digits 0 through 9.
2. `outputs/cfg_scale_ablation_digit_7.png`: Strip demonstrating how varying $w \in [0.0, 1.0, 2.5, 4.0, 7.0]$ sharpens digit '7' from the exact same starting noise seed.
