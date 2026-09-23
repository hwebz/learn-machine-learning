# Learn Machine Learning: From Foundations to Generative AI

A hands-on repository containing practical machine learning projects, ranging from classical tabular prediction to modern generative diffusion models.

---

## 📂 Projects in This Repository

### 1. 🌟 [Diffusion Models: From First Principles to Latent Diffusion](./diffusion_models)
A complete, 5-stage progressive curriculum implementing modern diffusion models from scratch:
- **[Stage 1: 2D Toy DDPM](./diffusion_models/01_toy_2d_diffusion)**: Direct coordinate point diffusion on Swiss Roll & Gaussian mixtures with sinusoidal time embeddings.
- **[Stage 2: Vision DDPM](./diffusion_models/02_mnist_ddpm)**: 28×28 grayscale image synthesis with a Convolutional U-Net and skip connections.
- **[Stage 3: Classifier-Free Guidance (CFG)](./diffusion_models/03_conditional_cfg)**: Controllable, class-prompted generation (0–9) using label dropout and guidance scale extrapolation.
- **[Stage 4: Accelerated Sampling (DDIM)](./diffusion_models/04_fast_sampling_ddim)**: Non-Markovian deterministic ODE sampling yielding a **15.8× speedup** (20 steps vs 300) and continuous latent space morphing (SLERP).
- **[Stage 5: Latent Diffusion Models (LDM)](./diffusion_models/05_latent_diffusion)**: Decoupling perceptual compression (Convolutional VAE) from semantic denoising (Latent U-Net with Spatial Cross-Attention), implementing the exact architecture behind **Stable Diffusion**.

👉 **[Read the Full Diffusion Models Walkthrough & Visual Guide](./diffusion_models/README.md)**

---

### 2. 🏠 [Housing Price Prediction](./housing_prediction)
End-to-end tabular machine learning pipeline:
- Exploratory Data Analysis (EDA) and feature preprocessing.
- Regression model training and artifact persistence (`joblib`).
- FastAPI prediction service and Docker containerization.

---

### 3. ⚡ [System Load Predictor](./system_load_predictor)
Production-grade system monitoring and workload forecasting:
- Machine learning engine for real-time CPU/RAM workload forecasting.
- FastAPI endpoints (v1 and v2) and synthetic load generators.
- Kubernetes deployment manifests (`deployment.yml`) and containerized microservices.
