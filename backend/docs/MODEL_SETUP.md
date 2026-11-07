# MAPORA AI Model Setup & Hardware Acceleration

This document describes how to configure computer vision models and hardware acceleration in MAPORA.

---

## 1. Monocular Depth Estimation Models (MiDaS / DPT)

MAPORA supports deep learning monocular depth estimation powered by PyTorch:

| Model Type | Architecture | Memory Footprint | Recommended Device | Inference Speed |
|---|---|---|---|---|
| `MiDaS_small` | EfficientNet-Lite | ~85 MB | CPU / GPU | ~25 FPS |
| `DPT_Hybrid` | Vision Transformer + ResNet | ~470 MB | CUDA GPU | ~8 FPS |
| `DPT_Large` | Dense Prediction Transformer | ~1.3 GB | High-End CUDA GPU | ~2 FPS |

### 1.1 Enabling Deep Learning Weights
To enable PyTorch transformer models, install `timm`:
```bash
pip install timm
```

Configure your preferred model in `.env`:
```env
MIDAS_MODEL_TYPE="MiDaS_small"
DEVICE="cpu"  # or "cuda"
```

Weights will be automatically downloaded to `./models_cache` on first run.

### 1.2 Graceful Geometric Fallback
If model weights are not present or internet connectivity is unavailable, MAPORA automatically activates its **Heuristic Geometric Depth** estimator. This ensures the reconstruction pipeline never crashes and produces valid architectural estimates based on horizon gradients and edge densities.

---

## 2. Hardware Acceleration (CUDA GPU)

If an NVIDIA GPU with CUDA support is installed:
1. Verify CUDA is detected:
   ```bash
   python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
   ```
2. Set in `.env`:
   ```env
   DEVICE="cuda"
   ```

---

## 3. Modular External SLAM Hooks (COLMAP / ORB-SLAM3)

For dense multi-view stereo or loop-closed keyframe bundle adjustment:
- Implement the `OdometryAdapter` interface in `app/reconstruction/odometry.py`.
- Point `ExternalSlamAdapter` to your installed binary path.

---

## 4. Model Licensing
- **MiDaS / DPT**: MIT License (Intel Intelligent Systems Lab).
- **OpenCV**: Apache License 2.0.
- **Trimesh**: MIT License.
