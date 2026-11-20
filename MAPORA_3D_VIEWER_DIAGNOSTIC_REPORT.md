# MAPORA — Critical 3D Viewer Reconstruction & Rendering Diagnostic Report

---

## 1. Executive Summary & Original Problem

When viewing a backend-reconstructed project in the MAPORA 3D Viewer (e.g. project `94c91ad5-9951-40e9-aac5-f8e09c3984fe` from video walkthrough upload and project `b5155b08-f0be-4d94-bd32-8f9559e92f3b` from photo upload), the 3D model exhibited critical visual anomalies:
1. **Pitch-Black Silhouette:** The entire 3D model appeared completely black, devoid of surface shading, depth perception, or directional illumination.
2. **Irregular, Jagged, Spike-Like Geometry:** Instead of clean, continuous architectural walls, the space was dominated by approximately 30 intersecting, 6-meter-long diagonal slabs slicing through room volumes at arbitrary 45-degree angles.
3. **Unrecognizable Room Structure:** Room boundaries and living zones were obscured by overlapping geometry cutting across open floors.
4. **Indistinguishable Floors and Walls:** Floor slabs were fragmented into disconnected islands with no visual material separation from walls.
5. **Single Detected Room:** The viewer reported only a single room ("Main Space") despite the walkthrough traversing multiple functional areas.

---

## 2. Root Cause Analysis

A rigorous, end-to-end technical audit revealed five distinct root causes spanning GLB export, line extraction, room segmentation, and Three.js client rendering:

### Root Cause A: Complete Absence of Normals in Exported GLB
- In `backend/app/reconstruction/model_3d_gen.py`, `trimesh.exchange.gltf.export_glb(scene)` was executed without `include_normals=True`.
- Raw GLTF primitive examination revealed:
  ```json
  "primitives": [{"attributes": {"POSITION": 1, "COLOR_0": 2}, "indices": 0, "mode": 4}]
  ```
  **0 of 34 meshes contained a `NORMAL` attribute.**
- In Three.js, when rendering `MeshStandardMaterial` with directional lights on geometries lacking normal vectors, the vertex shader evaluates normals as $(0, 0, 0)$. The lighting equation $(N \cdot L = 0)$ computes **0 diffuse illumination and 0 specular reflection**, forcing every polygon to render as an unlit black silhouette.

### Root Cause B: Zero PBR Materials in Exported GLB
- Trimesh exported raw geometries with vertex color arrays but **0 GLTF PBR Material definitions** (`materials: []`). Three.js fell back to a default unconfigured material that absorbed all illumination when normals were absent.

### Root Cause C: Unconstrained Hough Line Extraction Yielding Diagonal Chords
- In `backend/app/reconstruction/floor_plan_gen.py`, `cv2.HoughLinesP` was executed on a raw horizontal density slice with permissive thresholding (`threshold=25`, `minLineLength=8px`).
- In noisy 2D point clouds, the longest line of accumulated pixels frequently corresponds to diagonal chords cutting across the point cloud.
- The pipeline extracted ~30 diagonal segments ($dx \approx 6.0\text{m}, dy \approx 6.0\text{m}$), and `model_3d_gen.py` extruded every single segment into an 8.5-meter solid box across the interior space, creating a chaotic starburst of overlapping slabs.

### Root Cause D: Room Segmentation Leakage & Naming Mismatches
- In `floor_plan_gen.py`, free-space connected components (`cv2.connectedComponentsWithStats`) operated on inverted closed occupancy grids. Minor gaps in the outer wall perimeter allowed interior free space to leak into exterior margins, causing the entire building area to merge into a single component labeled "Main Space".
- In `Viewer3D.tsx`, GLTFLoader normalized node names with underscores (`Main_Space`), which failed exact string equality checks against database room names (`Main Space`), preventing room highlight and inspector synchronization.

### Root Cause E: Camera Target & Bounding Box Mismatch
- The generated model bounding box center was located at `[-0.87, 0.71, 1.33]`.
- Three.js OrbitControls targeted `[0, 0, 0]` with a fixed camera, causing the model to be viewed off-center and partially clipped.

---

## 3. GLB Inspection Statistics (Project `94c91ad5-9951-40e9-aac5-f8e09c3984fe`)

Detailed Trimesh and GLTF binary inspection of `scene_76c3a868-9210-421d-9987-da9a9470705a.glb`:

| Inspection Item | Measured Value | Assessment |
| :--- | :--- | :--- |
| **1. File Size** | 19,064 bytes (18.62 KB) | Compact binary glTF container |
| **2. Number of Meshes** | 34 meshes | 2 room floor slabs + 30 walls + 2 door elements |
| **3. Number of Vertices** | 272 vertices | Valid geometric boxes |
| **4. Number of Triangles** | 408 triangles (faces) | 12 triangles per box |
| **5. Number of Materials** | **0 materials** | **FAIL — Missing PBR materials** |
| **6. Material Colors** | None defined (raw vertex colors) | Untracked by shaders |
| **7. Material Opacity** | Default 1.0 | Opaque |
| **8. Normals** | **0 meshes with normals** | **CRITICAL FAIL — Causing black silhouette** |
| **9. Bounding Box Min** | `[-4.434, -0.040, -2.244]` | Offset from coordinate origin |
| **10. Bounding Box Max** | `[2.695, 1.450, 4.897]` | Bounding dimensions confirmed |
| **11. Dimensions (Extents)** | `7.13m (W) × 1.49m (H) × 7.14m (D)` | Realistic physical footprint |
| **12. Degenerate Triangles**| 0 degenerate faces | Mesh topology valid |
| **13. NaNs or Infinite Values** | None detected (0 NaNs, 0 Infs) | Numerical coordinates valid |
| **14. Mesh Overlaps** | **Severe (30 overlapping diagonal walls)** | **CRITICAL FAIL — Causing jagged geometry** |
| **15. Floating Geometry** | Disconnected door headers floating | Improper anchoring |

---

## 4. Remediation Plan

1. **Phase 2 (Three.js Client):**
   - Automatically recompute vertex normals on all imported geometries: `geometry.computeVertexNormals()`.
   - Apply clean architectural PBR materials: distinct off-white walls (`#f8f9fa`) and architectural slate/neutral floors (`#e2e5eb`), `side = THREE.DoubleSide`.
   - Balanced multi-directional lighting (ambient, hemisphere bounce, dual opposing directional lights) ensuring zero dark dead-zones.
   - Auto-center imported models at origin $(0, H/2, 0)$ and auto-frame OrbitControls camera based on bounding sphere radius.
2. **Phase 3 & 4 (Backend Geometry & Presentation):**
   - Implement orthogonal Manhattan regularization in `floor_plan_gen.py`, filtering out unconstrained diagonal lines and merging collinear segments within $0.35\text{m}$.
   - Prune chords crossing room free space.
   - Attach explicit PBR materials and export normals in `model_3d_gen.py` via `export_glb(scene, include_normals=True)`.
3. **Phase 5 (Room Detection):**
   - Seal perimeter gaps before connected component analysis to isolate multiple distinct functional rooms.
   - Support room name normalization (`Main_Space` $\leftrightarrow$ `Main Space`).
4. **Phase 6 & 7 (Verification & Testing):**
   - Re-run video and photo pipelines, verify GLB outputs, run full test suites (`pytest`, `npm test`, `npm run build`).

