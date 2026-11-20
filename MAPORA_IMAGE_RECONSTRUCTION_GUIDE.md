# MAPORA 2.0 — Multi-Image Upload & AI-Powered 2D/3D Reconstruction Guide

## 1. Overview & Architecture

MAPORA 2.0 introduces multi-image indoor reconstruction as a first-class input modality alongside the existing walkthrough video reconstruction pipeline. Users can upload one or multiple photographs of an indoor environment (e.g. living room, bedroom, office) to generate:

1. **A Structured 2D Floor Plan:** Metric room polygon boundaries, calculated perimeter/area, detected wall segments, and room classification.
2. **An Interactive 3D Spatial Model (GLB):** Watertight 3D extruded geometry with architectural walls, floor slab, ceiling height, and room bounding volumes rendered directly in Three.js / React Three Fiber.

```
                                 ┌───────────────────────────┐
                                 │   Frontend (React/Vite)   │
                                 │ Mode Switch: Video/Photos │
                                 └─────────────┬─────────────┘
                                               │
                         POST /api/v1/projects (or /projects/{id}/images)
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   FastAPI Backend API     │
                                 │  - Integrity Validation   │
                                 │  - Laplacian Blur Filter  │
                                 │  - Local Disk / S3 Store  │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                         ┌───────────────────────────────────────────┐
                         │   ImageReconstructionPipeline (9 Stages)  │
                         │                                           │
                         │ 1. Image Validation & Duplicate Detection │
                         │ 2. Preprocessing & Aspect-Ratio Scaling   │
                         │ 3. SIFT Feature Matching & RANSAC Pose   │
                         │ 4. Monocular Depth (MiDaS DPT ONNX)       │
                         │ 5. 3D Point-Cloud Fusion & Projection     │
                         │ 6. Semantic Segmentation (SegFormer-B0)   │
                         │ 7. 2D Floor-Plan Polygon Extraction       │
                         │ 8. 3D GLB Extrusion (Trimesh / glTF 2.0)  │
                         │ 9. Artifact Persistence & DB Updates      │
                         └─────────────────────┬─────────────────────┘
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         ▼                                           ▼
             ┌───────────────────────┐                   ┌───────────────────────┐
             │   2D Floor Plan JSON  │                   │    3D Spatial GLB     │
             │   - Room boundaries   │                   │   - Wall extrusions   │
             │   - Wall coordinates  │                   │   - Floor & ceiling   │
             │   - Area & metrics    │                   │   - Three.js viewers  │
             └───────────────────────┘                   └───────────────────────┘
```

---

## 2. Supported Image Formats & Constraints

| Parameter | Specification / Constraint |
|:---|:---|
| **Supported File Formats** | JPEG (`.jpg`, `.jpeg`), PNG (`.png`), WebP (`.webp`) |
| **Max File Size Per Image** | 25 MB (`MAX_IMAGE_UPLOAD_SIZE_BYTES = 26,214,400`) |
| **Recommended Image Count** | **4 to 12 images** with 40%+ visual overlap between adjacent viewpoints |
| **Minimum Image Count** | 1 image (triggers single-photo 2.5D approximation mode) |
| **Resolution Recommendation** | Minimum: 640 × 480; Recommended: 1080p (1920 × 1080) or 4K |
| **Aspect Ratio Handling** | Preserved automatically via letterbox / bounded scaling (max 1024px dimension) |
| **Blur Rejection** | Laplacian variance threshold $< 15.0$ indicates motion blur or defocus |

---

## 3. Recommended Indoor Image Capture Strategy

To achieve high reconstruction accuracy and complete room closure, follow this capture workflow:

```
                  [Corner A] ─── View 1 ───► (Facing Center)
                      │
                   View 2 ───► (Facing East Wall & Window)
                      │
                  [Corner B] ─── View 3 ───► (Facing South Door)
                      │
                   View 4 ───► (Wide View across Diagonal)
```

1. **Wide Coverage & Overlap:**
   - Stand in one corner of the room and take a shot toward the opposite corner.
   - Move along the perimeter (approx. 1.0 to 1.5 meters per step), capturing overlapping perspectives (aim for 40%–60% scene overlap between consecutive shots).
   - Ensure structural junctions (wall-floor corners, wall-ceiling intersections, door frames) are visible in at least two separate images.
2. **Lighting & Clarity:**
   - Turn on indoor ambient lighting to avoid deep shadows.
   - Avoid extreme backlight from windows; shoot with windows positioned perpendicular or behind camera whenever possible.
3. **Avoid Pure Rotation:**
   - Do not stand in the exact center and rotate on a single pivot point. Structure-from-Motion (SfM) requires baseline translation (lateral camera movement) to triangulate 3D depth and parallax.
4. **Single-Image Limitations:**
   - A single photo lacks parallax baseline. MAPORA generates a 2.5D perspective unprojection tagged with `quality_confidence: 0.50` and `measurements_available: false`. For complete metric floor plans, upload at least 4 photos.

---

## 4. REST API Reference

### 4.1 Create Project with Photos (`POST /api/v1/projects`)
Accepts either JSON or `multipart/form-data`. When uploading photos directly during creation:
- **Form Fields:**
  - `name`: Project display name (e.g., `"Living Room Scan"`).
  - `description`: Optional project description.
  - `input_type`: `"photo"`.
  - `photos` or `images`: Repeated file entries (one or multiple JPEG/PNG/WebP files).
- **Response:** HTTP 201 Created with `MapProject` JSON.

### 4.2 Batch Upload Photos to Existing Project (`POST /api/v1/projects/{project_id}/images`)
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: multipart/form-data`.
- **Form Data:** `files` (array of image files).
- **Response (201 Created):**
```json
{
  "project_id": "97e6be95-8e47-49f3-8fc7-789a74bfb4aa",
  "uploaded_count": 4,
  "images": [
    {
      "id": "e30cfab3-...",
      "filename": "living_view_01.jpg",
      "file_path": "projects/97e6.../images/e30c..._living_view_01.jpg",
      "file_size": 2048512,
      "width": 1920,
      "height": 1080,
      "laplacian_blur_score": 142.6,
      "created_at": "2026-11-08T16:30:00Z"
    }
  ]
}
```

### 4.3 List Uploaded Photos (`GET /api/v1/projects/{project_id}/images`)
Returns the array of `ImageUploadRead` objects containing file dimensions, blur scores, and timestamps.

### 4.4 Trigger Photo Reconstruction (`POST /api/v1/projects/{project_id}/reconstruct/images`)
Initiates the asynchronous multi-view reconstruction worker task.
- **Response (200 OK):**
```json
{
  "job_id": "0d951ce3-...",
  "status": "processing",
  "stage": "validating_images",
  "progress": 5,
  "message": "Validating uploaded images..."
}
```

### 4.5 Retrieve Floor Plan & 3D Scene
- `GET /api/v1/projects/{project_id}/floor-plan` → Returns structured 2D rooms and wall lines.
- `GET /api/v1/projects/{project_id}/scene` → Streams the generated binary `model/gltf-binary` (`.glb`) file.

---

## 5. Reconstruction Pipeline Stages

The `ImageReconstructionPipeline` executes 9 deterministic stages:

| Stage # | Stage Name | Description & Algorithms |
|:---|:---|:---|
| **1** | `validating_images` | Validates file signatures, decodes OpenCV matrices, computes perceptual hashes to reject exact duplicates, and calculates Laplacian blur variance ($\ge 15.0$). |
| **2** | `preprocessing` | Preserves original aspect ratios while bounding maximum dimension to 1024px for efficient CPU feature extraction. Normalizes dynamic range. |
| **3** | `extracting_features` & `estimating_cameras` | Computes SIFT keypoints and 128-dimensional local descriptors. Applies FLANN / BFMatcher with Lowe's ratio test ($d_1 / d_2 < 0.75$). Uses RANSAC epipolar geometry to estimate the Essential Matrix $E$ and recover camera rotation $R$ and translation $t$. Requires $\ge 15$ inliers. |
| **4** | `estimating_depth` | Runs MiDaS DPT ONNX monocular depth inference to extract dense relative inverse depth maps for each key viewpoint. |
| **5** | `reconstructing_spatial` | Back-projects depth pixels into camera coordinates $[X, Y, Z]$, rotates points by camera pose $[R \mid t]$, filters statistical outliers, and fuses into a unified coordinate frame. |
| **6** | `semantic_understanding` | SegFormer-B0 ONNX segmenter classifies indoor surfaces (Floor, Wall, Ceiling, Window, Door, Furniture) using ADE20K mapping. |
| **7** | `generating_floor_plan` | Extracts floor-wall boundary points, fits 2D boundary polygons, orthogonalizes wall segments, computes closed room areas ($m^2$), and generates standard MAPORA 2D floor-plan JSON. |
| **8** | `generating_3d_model` | Extrudes wall footprints vertically to the estimated ceiling height ($2.60\text{ m}$ pseudo-height), builds floor and ceiling planes, and exports a valid binary GLB using Trimesh. |
| **9** | `saving_artifacts` | Persists `floor_plan.json` and `scene.glb` to storage, creates `FloorPlanVersion`, updates project status to `completed`, and records audit logs. |

---

## 6. Single-Photo Fallback vs. Multi-Photo Mode

```
                ┌────────────────────────────────────┐
                │ User Uploads Photo(s) for a Space  │
                └─────────────────┬──────────────────┘
                                  │
                       Number of Valid Photos?
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
             [ 1 Photo ]                    [ >= 2 Photos ]
                 │                                 │
                 ▼                                 ▼
    ┌─────────────────────────┐       ┌─────────────────────────┐
    │  Single-Photo 2.5D Mode │       │  Multi-View SfM Mode    │
    │  - Perspective unproj   │       │  - SIFT feature match   │
    │  - Confidence: 0.50     │       │  - RANSAC pose recovery │
    │  - Measurements: False  │       │  - Inliers >= 15 check  │
    │  - Visual warning banner│       │  - Fused metric cloud   │
    └─────────────────────────┘       └────────────┬────────────┘
                                                   │
                                      Are inliers >= 15?
                                                   │
                                      ┌────────────┴────────────┐
                                      ▼                         ▼
                                    [Yes]                     [No]
                                      │                         │
                                      ▼                         ▼
                         ┌───────────────────────┐ ┌────────────────────────┐
                         │ Complete Metric Plan  │ │ InsufficientOverlap    │
                         │ & Watertight 3D GLB   │ │ Error (HTTP 422/Fail)  │
                         │ Confidence: 0.82-0.95 │ │ Informative UI warning │
                         └───────────────────────┘ └────────────────────────┘
```

- **Insufficient Overlap Error:** If photos have less than 15 inlier matches, MAPORA throws `InsufficientOverlapError: "Insufficient visual overlap between viewpoints (<15 matches). Please upload photographs with overlapping perspective."` rather than producing fabricated geometry.

---

## 7. Frontend User Guide

1. Navigate to **Upload** (`/upload`) in the MAPORA navigation bar.
2. Click the **"Indoor Photographs"** tab switcher.
3. Review the capture guidelines: minimum 4 photos recommended for full metric accuracy.
4. Drag and drop or browse to select your indoor images (`.jpg`, `.jpeg`, `.png`, `.webp`).
5. Inspect the live thumbnail grid:
   - Each thumbnail displays dimensions, file size, and remove button (`×`).
   - Use the **"Clear all"** button to start over if needed.
   - The photo counter badge indicates whether you have reached the recommended 4+ photo threshold.
6. Enter a Project Name and click **"Start Reconstruction"**.
7. Track live processing on `/projects/:id/processing`:
   - Watch the progress bar advance through `Validating images`, `Extracting features`, `Estimating camera positions`, `Reconstructing spatial geometry`, and `Generating 3D model`.
8. Once completed, explore:
   - **Overview:** Displays project type as `Photo Reconstruction` with total image count and quality confidence.
   - **2D Floor Plan:** View metric room polygons, wall lengths, and room areas in the Floor Plan Editor.
   - **3D Viewer:** Orbit, pan, zoom, and toggle wireframe mode over the extruded 3D spatial geometry.

---

## 8. Hardware & System Requirements

- **Operating System:** Windows 10/11, Linux, or macOS.
- **Python Version:** Python 3.11+.
- **Node.js Version:** Node.js v18+.
- **Inference Hardware:** Optimized for standard multi-core CPUs (e.g. Intel Core i5/i7/Ultra with Intel Iris Xe or AMD Ryzen). CUDA GPU is **not required**.
- **ONNX Runtimes:**
  - MiDaS DPT ONNX depth engine: 4 intra-op threads, GraphOptimizationLevel ORT_ENABLE_ALL.
  - SegFormer-B0 ONNX semantic engine: 4 intra-op threads, CPUExecutionProvider.

---

## 9. Troubleshooting & FAQ

### Q: Why did the reconstruction fail with "Insufficient visual overlap"?
- **Cause:** The uploaded photographs were taken facing completely opposite directions without bridge frames, or the room had featureless blank walls.
- **Solution:** Take 2–3 intermediate photos connecting the views, ensuring doors, corners, or furniture remain visible across consecutive shots.

### Q: Why does my single photo show "Estimated 2.5D approximation"?
- **Explanation:** Monocular depth from a single viewpoint cannot measure metric scale or reveal surfaces occluded behind objects. MAPORA flags single-photo models with `measurements_available = false` to guarantee metric integrity. Upload 4+ overlapping photos for calibrated metric reconstruction.

### Q: How do I run the full test suite locally?
```powershell
# Frontend tests & production build
npm test

# Backend image reconstruction test suite
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_image_reconstruction.py -v

# Regression check on video pipeline
.\.venv\Scripts\python.exe -m pytest tests/test_reconstruction.py -v
```

