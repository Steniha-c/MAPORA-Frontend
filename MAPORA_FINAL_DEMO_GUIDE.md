# MAPORA 2.0: Final Demonstration Guide & Viva Walkthrough Script
## Complete Live Presentation Guide for Evaluation Committee

---

## 1. Pre-Demonstration Setup & Verification

Before presenting to the evaluation committee, verify that the environment is initialized and running.

### 1.1 Service Verification
Ensure both the FastAPI backend and Vite frontend are active:

| Service | Local URL | Command to Start (if needed) |
| :--- | :--- | :--- |
| **Backend (FastAPI)** | `http://127.0.0.1:8000` | `cd backend; .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000` |
| **Frontend (Vite)** | `http://localhost:5173` | `npm run dev` |
| **API Documentation** | `http://127.0.0.1:8000/docs` | Built-in Swagger UI |

### 1.2 Demonstration Credentials
- **Administrator Email:** `admin@mapora.io`
- **Administrator Password:** `AdminMapora2026!`
- **Role:** `admin` (Full access to all surveyor projects, exports, and admin observability metrics)

### 1.3 Quick System Health Verification
Open a PowerShell terminal or browser tab:
1. Visit `http://127.0.0.1:8000/docs` &rarr; verify OpenAPI specification loads.
2. Visit `http://localhost:5173/` &rarr; verify the MAPORA landing page and dark architectural aesthetic loads cleanly.

---

## 2. Six-Stage Live Demonstration Script

### Stage 1: System Overview & Resilient Authentication (2 Minutes)
**Objective:** Introduce MAPORA's core problem statement, architectural foundations, and industrial-grade session security.

1. **Open the Homepage:**
   - Navigate to `http://localhost:5173/`.
   - **Presenter Talking Point:**
     > *"Welcome committee members. This is MAPORA—an AI-driven spatial mapping platform designed to eliminate reliance on multi-thousand-dollar LiDAR hardware by reconstructing structured 2D architectural floor plans and 3D spatial models directly from standard smartphone videos or multi-angle photos."*
2. **Access the Login Screen:**
   - Click **Sign In** in the top navigation bar or go directly to `http://localhost:5173/login`.
   - Enter credentials:
     - Email: `admin@mapora.io`
     - Password: `AdminMapora2026!`
   - Click **Sign in**.
3. **Highlight Technical Architecture:**
   - **Presenter Talking Point:**
     > *"Authentication uses cryptographic JWT tokens with RFC 6750 Bearer headers. The frontend implements proactive token life-cycle monitoring: it inspects token expiration client-side, runs an asynchronous single-flight refresh mutex, and features an Axios/fetch 401 interceptor that automatically recovers expired sessions without disrupting ongoing uploads or workflows."*

---

### Stage 2: MAPORA 2.0 Multi-Photo Indoor Reconstruction (3 Minutes)
**Objective:** Demonstrate the newly engineered multi-photo indoor reconstruction pipeline and explain epipolar geometry principles.

1. **Navigate to Project Creation:**
   - Click **New Project** or navigate to `http://localhost:5173/projects/new`.
2. **Select Photo Mode:**
   - Toggle the modality switcher from **Walkthrough Video** to **Indoor Photographs**.
   - Note the UI updates: photo count tracker, upload batch guidance, and camera requirements.
3. **Select Sample Photos:**
   - Drag and drop or browse to select 3–5 indoor room photographs (or use the provided test suite images).
   - Give the project a name: e.g., `"Executive Conference Suite"`.
4. **Initiate Processing:**
   - Click **Upload and Reconstruct**.
   - **Presenter Talking Point:**
     > *"MAPORA 2.0 uses multi-view Structure-from-Motion (SfM). It detects multi-scale ORB keypoints, matches features across image pairs using Lowe's ratio test, and computes the Fundamental and Essential matrices with RANSAC outlier rejection. Matched feature rays are triangulated into a 3D point cloud and fused with monocular depth maps."*
5. **Discuss Fallback Integrity:**
   - **Presenter Talking Point:**
     > *"To preserve academic integrity, MAPORA never fabricates geometry. If a user uploads only a single image where multi-view parallax is impossible, the backend activates a 2.5D single-photo fallback and clearly marks the reconstruction with degraded confidence (45% confidence) rather than pretending multi-view triangulation occurred."*

---

### Stage 3: Walkthrough Video Reconstruction Pipeline (3 Minutes)
**Objective:** Walk through the video reconstruction pipeline stages and show real-time progress telemetry.

1. **Navigate to Processing Tracker:**
   - Observe the live status screen at `/projects/{id}/processing` or review an active reconstruction job.
2. **Explain the 6-Stage Pipeline Execution:**
   - **Stage 1 (Keyframe Extraction):** Frames sampled at 2 Hz; Laplacian blur variance filter ($\text{Var}(\nabla^2 I) \ge 100.0$) discards blurred frames.
   - **Stage 2 (Monocular Depth Estimation):** Pretrained MiDaS DPT ONNX model predicts relative inverse depth maps, scaled to metric dimensions via camera ground-plane priors.
   - **Stage 3 (Temporal Flow Consistency):** Dense Farneback optical flow tracks motion vectors between consecutive frames to warp and blend depth maps, eliminating flickering.
   - **Stage 4 (Visual Odometry & Camera Motion):** 5-point essential matrix decomposition tracks the camera's trajectory along the $(X, Z)$ ground plane.
   - **Stage 5 (Semantic Scene Segmentation):** SegFormer-B0 ONNX parses each frame into ADE20K classes (`wall`, `floor`, `ceiling`, `door`, `window`).
   - **Stage 6 (Floor Plan & Mesh Synthesis):** Bird's Eye View (BEV) orthographic projection and Trimesh 2.5D solid extrusion.

---

### Stage 4: 2D Floor Plan Editor & Topological Pathway Graph (4 Minutes)
**Objective:** Showcase interactive CAD editing, real room dimensions, door connectivity, and topological pathway graphs.

1. **Open the 2D Editor:**
   - Navigate to `/projects/{id}/floor-plan` (or click **2D Floor Plan** on a completed project).
2. **Examine the Reconstructed Geometry:**
   - Point out that the canvas displays **BACKEND GEOMETRY**, not a placeholder sample.
   - Click on different rooms: notice the **Spatial Inspector** on the right displays real computed surface areas (e.g., `18.42 m²`) and real bounding box dimensions (e.g., `4.80 × 3.84 m`).
3. **Demonstrate Topological Pathways:**
   - Click the **Pathways** button in the top toolbar (compass icon).
   - Observe the dashed blue pathways rendered directly on the floor plan.
   - **Presenter Talking Point:**
     > *"MAPORA computes a topological room connectivity graph. Our spatial algorithm analyzes detected door segments: whenever a door opening bridges two adjacent room envelopes within 1.2 meters, an edge is created between the room centroids. The dashed blue polyline shows the navigable pathway through the door midpoint ($C_1 \to D_{\text{mid}} \to C_2$). If a room has no detected doors, our algorithm flags it as a disconnected room."*
4. **Demonstrate Interactive Editing & Backend Persistence:**
   - Select a room (e.g., `"Room 01"`).
   - In the right-side inspector, edit the label to `"Master Suite"`.
   - Click **Save changes to backend**.
   - Notice the success notification: `"Floor plan updates saved to backend successfully."`
   - Refresh the page to prove to the committee that the update was persisted to the database via `PATCH /projects/{id}/floor-plan`!

---

### Stage 5: 3D Spatial Model & WebGL Viewer (3 Minutes)
**Objective:** Demonstrate real-time 3D navigation, solid wall extrusion, and door cutouts.

1. **Switch to 3D View:**
   - Click the **3D View** button in the header or navigate to `/projects/{id}/3d`.
2. **Interact with the 3D Scene:**
   - **Rotate:** Left-click and drag to rotate the camera around the structure.
   - **Pan:** Right-click and drag to pan across rooms.
   - **Zoom:** Scroll mouse wheel to zoom into interior spaces.
3. **Highlight Reconstructed Architectural Features:**
   - **Presenter Talking Point:**
     > *"The 3D model is generated dynamically by Trimesh on the backend and streamed as a binary GLTF (.glb) asset. Notice the solid wall extrusion with a standard 2.8m ceiling height and boolean cutouts for detected door portals. Three.js renders the scene in real time with OrbitControls, directional lighting, and ambient occlusion."*

---

### Stage 6: CAD/BIM Multi-Format Exports & Admin Dashboard (2 Minutes)
**Objective:** Demonstrate interoperability with architectural tools (AutoCAD, Revit, Blender) and enterprise administrative observability.

1. **Export Formats:**
   - At the bottom of the floor plan or project page, showcase the available export buttons:
     - **DXF:** Standard AutoCAD exchange format with separate layers for walls and doors.
     - **PDF:** Architectural plan sheet with scale bar and title block.
     - **SVG:** Vector graphic for web or print publishing.
     - **GLB & OBJ:** Standard 3D formats for Blender, Revit, 3ds Max, or game engines.
   - Click **OBJ** or **GLB** to download the genuine 3D model.
2. **Admin Observability Dashboard:**
   - Navigate to `http://localhost:5173/admin`.
   - Point out the unified metrics:
     - Total registered surveyors and administrators.
     - Aggregated storage tracking both **Video Uploads** and **Photo Uploads**.
     - Real-time job distribution (Queued, Processing, Completed, Failed).
   - **Presenter Talking Point:**
     > *"The administration portal provides system-wide operational observability, tracking storage usage across both video and photo modalities with strict role-based access control preventing unauthorized surveyor access."*

---

## 3. Anticipated Viva Committee Questions & Quick Answers

| Question | Short Defensible Answer |
| :--- | :--- |
| **"Is this a complete SLAM system?"** | *"MAPORA implements monocular visual odometry with temporal optical flow depth fusion, not full bundle-adjusted SLAM. It tracks relative motion and projects geometry, but does not perform pose graph loop closure. We document this limitation honestly."* |
| **"How do you resolve metric scale from a single camera?"** | *"Monocular depth estimation is inherently scale-ambiguous. MAPORA resolves metric scale by assuming a standard camera eye-level height ($1.4\text{m}$) relative to the detected floor semantic plane, scaling inverse depth outputs accordingly."* |
| **"Why SegFormer over Mask R-CNN or YOLO?"** | *"SegFormer-B0 uses a lightweight hierarchical Transformer encoder with an efficient MLP decoder. It delivers high mIoU on ADE20K indoor classes while running inference in under 150ms on standard CPUs without GPU requirements."* |
| **"How do you handle disconnected rooms in the floor plan?"** | *"Our spatial connectivity algorithm computes Euclidean distances between room boundary segments and detected door polygons. Rooms separated by walls without a detected door within $1.2\text{m}$ are identified as disconnected and flagged in the UI."* |

---

## 4. Emergency Troubleshooting Procedures

- **Issue:** Browser shows `"Failed to fetch"` during video or photo upload.
  - **Resolution:** Verify backend is running on `127.0.0.1:8000`. Test endpoint with `curl http://127.0.0.1:8000/api/v1/health`.
- **Issue:** Session displays `"Invalid or expired access token"`.
  - **Resolution:** Click **Sign In Again** or log in with `admin@mapora.io` / `AdminMapora2026!`. Proactive token refresh handles ongoing sessions automatically.
- **Issue:** Port 8000 or 5173 is already occupied.
  - **Resolution:** Check running tasks with PowerShell: `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force`.

