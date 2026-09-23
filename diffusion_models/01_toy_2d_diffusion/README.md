# Stage 1: 2D Toy Distribution Diffusion Models (DDPM)

Welcome to Stage 1! Before diving into heavy U-Net convolutions or image latent spaces, we start here: **learning diffusion on 2D coordinates $(x_1, x_2)$**.

---

## 🎯 Why This Stage is So Powerful

1. **You can actually *see* diffusion happening**:
   - In image diffusion models, noisy steps look like meaningless TV static.
   - In 2D space, you can literally watch 2,500 points scatter into a cloud of Gaussian noise ($q$), and then see the neural network steer random noise back into a crisp Swiss Roll spiral ($p_\theta$).
2. **Lightning Fast**:
   - The neural network has ~100k parameters.
   - It trains in ~20 seconds on CPU or GPU.
3. **Identical Math to Stable Diffusion**:
   - Forward schedule $\beta_1 \dots \beta_T$ and $\bar{\alpha}_t$.
   - Sinusoidal timestep embeddings for $t$.
   - $\epsilon$-prediction objective $\mathcal{L}_{simple} = \|\epsilon - \epsilon_\theta(x_t, t)\|^2$.
   - Reverse Langevin-like denoising loop.

---

## 📐 Mathematical Formulation

### 1. Forward Noising ($q$)
Starting from clean coordinate pair $x_0 \in \mathbb{R}^2$, we add Gaussian noise at each timestep $t \in [1, \dots, T]$:
$$q(x_t | x_{t-1}) = \mathcal{N}\left(x_t; \sqrt{1 - \beta_t} x_{t-1}, \beta_t \mathbf{I}\right)$$

Thanks to the properties of Gaussian distributions, we don't have to step one-by-one:
$$x_t = \sqrt{\bar{\alpha}_t} x_0 + \sqrt{1 - \bar{\alpha}_t} \epsilon, \quad \text{where } \epsilon \sim \mathcal{N}(0, \mathbf{I})$$
- $\alpha_t = 1 - \beta_t$
- $\bar{\alpha}_t = \prod_{s=1}^t \alpha_s$

See implementation in [`diffusion.py`](./diffusion.py#L74) -> `q_sample()`.

### 2. Network Architecture & Time Embeddings
Our model is $\epsilon_\theta(x_t, t)$:
- Input: coordinate $x_t \in \mathbb{R}^2$ and timestep $t \in \{0, \dots, T-1\}$.
- Timestep $t$ is mapped through sinusoidal positional embeddings:
  $$\text{PE}_{(t, 2i)} = \sin\left(\frac{t}{10000^{2i/d}}\right), \quad \text{PE}_{(t, 2i+1)} = \cos\left(\frac{t}{10000^{2i/d}}\right)$$
- Output: predicted noise $\hat{\epsilon} \in \mathbb{R}^2$.

See implementation in [`model.py`](./model.py#L22) -> `SinusoidalPosEmb` and `ToyMLPDiffusion`.

### 3. Training Objective
$$\mathcal{L}_{simple}(\theta) = \mathbb{E}_{t, x_0, \epsilon} \left[ \| \epsilon - \epsilon_\theta(x_t, t) \|^2 \right]$$
We sample random $x_0$, random $t$, random $\epsilon$, compute $x_t$, and backpropagate the MSE between true $\epsilon$ and predicted $\hat{\epsilon}$.

### 4. Reverse Sampling ($p_\theta$)
Starting at $t = T$ with pure noise $x_T \sim \mathcal{N}(0, \mathbf{I})$, we step backward:
$$x_{t-1} = \frac{1}{\sqrt{\alpha_t}} \left( x_t - \frac{\beta_t}{\sqrt{1 - \bar{\alpha}_t}} \epsilon_\theta(x_t, t) \right) + \sigma_t z, \quad z \sim \mathcal{N}(0, \mathbf{I}) \text{ (if } t > 0)$$

---

## 🏃 Hands-On Execution Guide

### Step 1: Visually Inspect Forward Noising (No Training Needed!)
Run this first to see the data dissolve into noise:
```bash
python inspect_forward.py --dataset swiss_roll
```
*Output image:* `outputs/forward_diffusion_swiss_roll.png`

Try other datasets too:
```bash
python inspect_forward.py --dataset eight_gaussians
python inspect_forward.py --dataset two_moons
```

### Step 2: Train the Denoising Model
```bash
python train.py --dataset swiss_roll --epochs 40 --batch_size 256
```
- Trains in ~15–30 seconds.
- Saves the trained model to `checkpoints/toy_ddpm_swiss_roll.pt`.
- Saves the loss curve to `outputs/loss_curve_swiss_roll.png`.

### Step 3: Sample & Visualize Denoising Trajectory
```bash
python sample.py --checkpoint checkpoints/toy_ddpm_swiss_roll.pt
```
- Generates `outputs/reverse_denoising_swiss_roll.png`: Shows pure noise $x_T$ crystallizing into a spiral through timesteps $T \to 0$.
- Generates `outputs/comparison_swiss_roll.png`: Side-by-side comparison of Ground Truth vs Model Generated points.
