# MAPORA 2.0: Technical Viva Defense & Oral Examination Preparation Guide
## Comprehensive Technical Defense Manual & 30 High-Yield Viva Questions

---

## Part 1: Core Theoretical Foundations

### 1.1 Epipolar Geometry & The Essential Matrix
- **Epipolar Plane:** The plane formed by two camera optical centers $C_1, C_2$ and a 3D scene point $P$.
- **Epipoles ($e_1, e_2$):** The intersection of the baseline vector $(C_1 - C_2)$ with the image planes.
- **Epipolar Lines:** Projections of the line of sight connecting a camera center to point $P$ onto the other camera's image plane. Point correspondences must lie along these lines, reducing 2D spatial search to 1D linear search.
- **Fundamental Matrix ($F$):** Relates uncalibrated pixel coordinates between two views:
  $$x_2^T F x_1 = 0 \quad \text{where } F = K_2^{-T} E K_1^{-1}$$
- **Essential Matrix ($E$):** Encodes extrinsic rotation $R$ and translation $t$ in normalized camera coordinates:
  $$E = [t]_\times R$$
  where $[t]_\times$ is the skew-symmetric matrix:
  $$[t]_\times = \begin{bmatrix} 0 & -t_z & t_y \\ t_z & 0 & -t_x \\ -t_y & t_x & 0 \end{bmatrix}$$
- **Singular Value Decomposition (SVD):** Decomposing $E$ via SVD yields two possible rotations and two translation directions, resulting in four candidate pose configurations. The true pose is determined by triangulating a 3D point and verifying the cheirality condition (the point must lie in front of both cameras: $Z_1 > 0, Z_2 > 0$).

### 1.2 Monocular Scale Ambiguity
A single uncalibrated pinhole camera maps 3D points $(X, Y, Z)$ to 2D image coordinates $(u, v)$ via perspective projection:
$$u = f_x \frac{X}{Z} + c_x, \quad v = f_y \frac{Y}{Z} + c_y$$
Multiplying $(X, Y, Z)$ by any scalar $\lambda > 0$ yields identical pixel coordinates $(u, v)$. Hence, monocular systems cannot recover absolute metric scale from pure image pixels without an external scale reference (e.g., known camera mounting height, fiducial markers, or known object dimensions). MAPORA solves this by estimating the camera's eye-level height ($1.4\text{m}$) relative to the detected floor semantic plane.

### 1.3 MiDaS Monocular Depth Estimation
MiDaS formulates monocular depth estimation invariant to absolute scale and shift by optimizing scale-and-shift invariant loss functions:
$$\mathcal{L}_{\text{ssi}}(d^*, d) = \frac{1}{2N} \sum_{i=1}^N \left( \hat{d}_i^* - \hat{d}_i \right)^2$$
where $\hat{d}^*$ and $\hat{d}$ are normalized to zero translation and unit scale. MiDaS outputs **disparity (relative inverse depth)**:
$$d(u, v) \propto \frac{1}{Z(u, v)}$$
Points with high disparity values are close to the lens; low disparity corresponds to distant background structures.

### 1.4 Dense Optical Flow (Farneback Method)
The Gunnar Farneback algorithm models local image neighborhoods using quadratic polynomial expansions:
$$f_1(\mathbf{x}) \approx \mathbf{x}^T A_1 \mathbf{x} + \mathbf{b}_1^T \mathbf{x} + c_1$$
Under translation displacement $\mathbf{d}$, the second image is modeled as:
$$f_2(\mathbf{x}) = f_1(\mathbf{x} - \mathbf{d}) \approx \mathbf{x}^T A_2 \mathbf{x} + \mathbf{b}_2^T \mathbf{x} + c_2$$
Equating coefficients provides direct linear solutions for dense displacement field $\mathbf{d} = (u, v)$ across all pixels, which MAPORA uses to warp and temporally smooth monocular depth maps.

### 1.5 SegFormer Semantic Architecture
Unlike classical CNNs (e.g., FCN, DeepLabv3) that use heavy dilated convolutions, SegFormer-B0 uses:
1. **Hierarchical Transformer Encoder:** Extracts multi-scale feature maps at $1/4, 1/8, 1/16,$ and $1/32$ resolutions using spatial-reduction self-attention.
2. **Overlapped Patch Merging:** Preserves local pixel continuity at patch boundaries.
3. **All-MLP Decoder:** Aggregates multi-scale contextual features with a lightweight multi-layer perceptron, avoiding complex dilation convolutions and enabling real-time CPU inference ($< 150\text{ms}$).

---

## Part 2: 30 High-Yield Technical Viva Questions & Defensible Answers

### Category 1: Computer Vision & Sensor Geometry

#### Q1: Why can't a single camera measure absolute metric scale directly?
**Answer:** Perspective projection collapses 3D rays into 2D sensor pixels. A small room viewed from close up and an identical large hall viewed from far away produce mathematically identical pixel projections if all coordinates are scaled by a constant factor $\lambda$. Monocular vision therefore has an inherent scale ambiguity ($E = [t]_\times R$ provides translation $t$ normalized to unit length $\|t\| = 1$). To recover metric scale, MAPORA uses a ground-plane floor contact prior, assuming standard camera eye-level height ($1.4\text{m}$).

#### Q2: What is the difference between the Fundamental Matrix and the Essential Matrix?
**Answer:** The Fundamental Matrix ($F$) operates in unnormalized pixel coordinates ($p_2^T F p_1 = 0$) and incorporates intrinsic camera calibration matrices: $F = K_2^{-T} E K_1^{-1}$. It has 7 degrees of freedom. The Essential Matrix ($E$) operates in normalized camera coordinates ($x_2^T E x_1 = 0$) where intrinsic effects are removed: $x = K^{-1} p$. It has 5 degrees of freedom (3 for rotation, 2 for direction of translation) and satisfies the trace constraint: $2EE^TE - \text{tr}(EE^T)E = 0$.

#### Q3: Why does MAPORA use RANSAC during feature matching and pose estimation?
**Answer:** Feature matching algorithms (like ORB with descriptor distance) inevitably produce false matches (outliers) due to repetitive patterns, motion blur, and illumination changes. The 8-point and 5-point algorithms are non-robust estimators; even a single outlier can distort the estimated epipolar geometry. RANSAC randomly samples minimal feature subsets, estimates model parameters, and identifies the model that maximizes inlier consensus, discarding spurious correspondences.

#### Q4: How does the 5-point algorithm differ from the 8-point algorithm?
**Answer:** The 8-point algorithm (Longuet-Higgins) treats the 9 elements of $E$ linearly, ignoring the non-linear algebraic constraints that two singular values of $E$ must be equal and the third zero. It requires at least 8 point pairs and can degenerate on planar scenes. Nistér's 5-point algorithm enforces these cubic polynomial constraints directly, requiring only 5 point correspondences and remaining robust even when all points lie on a common plane (e.g., a flat indoor wall).

#### Q5: What is the cheirality condition during Essential Matrix decomposition?
**Answer:** Decomposing $E$ into rotation $R$ and translation $t$ via SVD yields 4 mathematical candidate solutions: $(R_1, +t), (R_1, -t), (R_2, +t), (R_2, -t)$. The cheirality check triangulates a 3D point using each candidate pose and verifies that the resulting 3D point has positive depth ($Z > 0$) with respect to both camera coordinate frames (i.e., the point is in front of both cameras). Exactly one of the four pairs satisfies this physical reality.

#### Q6: How does monocular depth estimation differ from stereo depth estimation?
**Answer:** Stereo depth uses two calibrated cameras with a known physical baseline $B$. It computes disparity $d$ via correspondence search along epipolar lines, allowing exact metric depth calculation: $Z = \frac{f \cdot B}{d}$. Monocular depth estimation uses a single image and predicts relative inverse depth through learned monocular cues (vanishing points, occlusion boundaries, texture gradients, haze, and familiar object sizes) encoded in deep convolutional or transformer weights.

---

### Category 2: Deep Learning & Model Optimization

#### Q7: Why use MiDaS rather than supervised depth estimators like NYUv2 Depth?
**Answer:** Models trained purely on indoor datasets like NYUv2 overfit to specific sensor baselines and narrow indoor domain distributions. MiDaS was trained on a multi-objective loss across 12 diverse datasets comprising over 2 million images using scale-and-shift invariant losses. This makes its zero-shot generalization to diverse unseen indoor rooms significantly more robust than supervised models trained on single datasets.

#### Q8: How is inverse depth converted into a metric 3D point cloud?
**Answer:** MiDaS outputs normalized inverse depth (disparity) $\tilde{d} \in [0, 1]$. We first invert this to obtain relative depth: $\tilde{Z} = 1 / (\tilde{d} + \epsilon)$. We then determine metric scaling factor $s$ using the camera height ground-plane prior: $s = H_{\text{camera}} / \bar{Y}_{\text{floor}}$. Metric depth is $Z = s \cdot \tilde{Z}$. Given intrinsic camera matrix $K$ with focal lengths $(f_x, f_y)$ and principal point $(c_x, c_y)$, each pixel $(u, v)$ is back-projected:
$$X = \frac{(u - c_x) Z}{f_x}, \quad Y = \frac{(v - c_y) Z}{f_y}, \quad Z = Z$$

#### Q9: What advantages does SegFormer offer over DeepLabV3+ for indoor segmentation?
**Answer:** DeepLabV3+ relies on heavy atrous (dilated) convolutions and spatial pyramid pooling, which have high memory footprints and high computational complexity on CPUs. SegFormer-B0 uses a lightweight hierarchical Transformer encoder with sequence reduction, capturing global contextual dependencies (e.g., distinguishing a large continuous wall from a closed door) with only 3.7 million parameters. It runs inference in under 150ms on CPU, compared to >600ms for DeepLabV3+.

#### Q10: Why did MAPORA choose ONNX Runtime instead of raw PyTorch for inference?
**Answer:** PyTorch incurs significant runtime overhead from dynamic graph building, autograd tracking, and Python GIL locking. ONNX Runtime optimizes the computation graph offline by fusing operators (e.g., Conv + BatchNorm + ReLU), eliminating redundant memory copies, and leveraging multi-threaded AVX2/AVX-512 SIMD vectorization on x86 CPUs. This achieves a 2.5× to 4× speedup on CPU hardware without requiring an external GPU.

#### Q11: How do you prevent inter-frame depth flickering in video processing?
**Answer:** Single-frame monocular depth estimates suffer from high-frequency temporal variance between consecutive frames due to minor lighting and exposure shifts. MAPORA computes dense optical flow using the Farneback algorithm between frame $t-1$ and $t$, warps the previous depth map $D_{t-1}$ to the current frame coordinates using the flow vectors, and applies an exponential moving average:
$$D_t(x, y) = \alpha D_t^{\text{raw}}(x, y) + (1 - \alpha) \mathcal{W}(D_{t-1}(x, y), \mathbf{u})$$
with $\alpha \approx 0.65$.

#### Q12: How are ADE20K semantic classes mapped to MAPORA architectural components?
**Answer:** ADE20K contains 150 diverse semantic categories. MAPORA filters and groups these into structural primitives:
- Class 0 (`wall`) &rarr; 3D vertical wall extrusions and 2D floor plan boundaries.
- Class 3 (`floor`) &rarr; Ground contact plane, camera height calibration, and navigable area.
- Class 5 (`ceiling`) &rarr; Ceiling height normalization ($2.8\text{m}$).
- Class 14 (`door`) &rarr; Inter-room transition portals, topological graph edges, and 3D door cutouts.
- Class 8 (`window`) &rarr; Wall boundary openings.

---

### Category 3: Motion Estimation & SLAM Limitations

#### Q13: Is MAPORA a complete SLAM (Simultaneous Localization and Mapping) system?
**Answer:** No. To maintain academic and engineering honesty: MAPORA implements **monocular visual odometry with temporal optical flow consistency**, not full closed-loop SLAM. Full SLAM systems (such as ORB-SLAM3) maintain a global co-visibility graph, execute continuous bundle adjustment over keyframe windows, and run pose graph optimization upon detecting loop closures. MAPORA performs frame-to-frame odometry and accumulates geometry, but does not solve the global non-linear optimization problem required for drift-free long loop closure.

#### Q14: What is the primary failure mode of monocular visual odometry over long loops?
**Answer:** Cumulative drift. Because translation scale is unobservable in monocular systems, small scale errors and rotation inaccuracies in each frame-to-frame estimation compound over time without bound. In a large circular walkthrough, the reconstructed trajectory will fail to close the loop, resulting in duplicate or misaligned room walls unless corrected by loop closure bundle adjustment or external anchors.

#### Q15: How does MAPORA mitigate odometry drift in floor plan generation?
**Answer:** Rather than relying exclusively on camera trajectory integration, MAPORA projects semantic `wall` points onto an orthographic Bird's Eye View (BEV) ground plane and applies the Probabilistic Hough Transform with Manhattan-world orthogonal regularization (assuming indoor walls meet at $90^\circ$ or $180^\circ$ angles). This geometric constraint snaps drifting point clusters into clean, rectangular room envelopes.

#### Q16: Why are blurred frames discarded during keyframe extraction?
**Answer:** Camera motion blur destroys high-frequency spatial gradients, causing feature detectors (ORB/SIFT) to fail and producing inaccurate optical flow vectors. MAPORA evaluates the Laplacian variance of each frame: $\sigma^2 = \text{Var}(\nabla^2 I)$. Frames with variance below $100.0$ are discarded, ensuring only crisp keyframes are passed to depth and odometry models.

#### Q17: What happens if an indoor walkthrough contains dynamic objects (e.g., people walking)?
**Answer:** Dynamic objects violate the static scene assumption underlying both epipolar geometry and visual odometry. If tracked features lie on a moving person, the calculated Essential Matrix will incorporate non-rigid motion vectors. MAPORA’s semantic segmenter masks out dynamic classes (ADE20K `person`, `dog`, `cat`), and RANSAC treats dynamic feature matches as statistical outliers, rejecting them from the motion calculation.

---

### Category 4: Floor Plan & Computational Geometry

#### Q18: Explain the Bird's Eye View (BEV) projection algorithm.
**Answer:** Given a 3D point cloud where each point has coordinates $(X, Y, Z)$ and semantic class label $C$:
1. Points classified as `wall` are isolated.
2. A vertical height band is applied: $Y \in [0.2\text{m}, 2.4\text{m}]$ (eliminating floor clutter like shoes or ceiling fixtures).
3. The remaining points are projected orthographically onto the horizontal plane $(X, Z)$.
4. The 2D coordinates are rasterized into an occupancy grid accumulator, where pixel intensity corresponds to vertical wall point density.

#### Q19: How does MAPORA construct the Topological Room Connectivity Graph?
**Answer:**
1. **Nodes ($V$):** Computed as the geometric 2D centroids $C_i = (x_i, y_i)$ of each reconstructed room envelope.
2. **Door Association:** Detected door segments are mapped to 2D line segments.
3. **Spatial Bridging:** For each door $D_k$, the algorithm computes the Euclidean distance to all room boundaries. If a door lies within $1.2\text{ meters}$ of two distinct rooms $R_i$ and $R_j$, an undirected edge $e = (R_i, R_j)$ is inserted into graph $G$.
4. **Navigable Waypoints:** A 3-point piecewise pathway is synthesized connecting $C_i \to D_{k,\text{midpoint}} \to C_j$.

#### Q20: What is a "disconnected room" and how does the system detect it?
**Answer:** A disconnected room is an indoor space that has been reconstructed geometrically (walls and area exist), but possesses zero detected door edges in the topological connectivity graph. This occurs when doors were closed during recording, obstructed by furniture, or missed by the semantic segmenter. The system checks the degree of each node $\text{deg}(v) = 0$, flags the room ID in `disconnectedRooms`, and renders an alert banner in the 2D editor to prompt surveyor review.

#### Q21: How are room surface areas ($m^2$) calculated?
**Answer:** For axis-aligned rectangular rooms, area is simply $\text{Width} \times \text{Height}$ in calibrated metric units. For non-rectangular or multi-sided polygons, MAPORA applies the Shoelace Formula (Gauss's area formula):
$$A = \frac{1}{2} \left| \sum_{i=1}^{n-1} (x_i y_{i+1} - x_{i+1} y_i) + (x_n y_1 - x_1 y_n) \right|$$
where $(x_i, y_i)$ are the ordered 2D vertices of the room polygon in meters.

#### Q22: How does Trimesh perform 2.5D spatial extrusion for 3D GLB models?
**Answer:** Trimesh takes the 2D planar polygon representing the outer room perimeter and interior room boundaries, triangulates the 2D polygon using Delaunay triangulation or ear-clipping to form the floor and ceiling caps, and creates rectangular vertical quads connecting each 2D edge at $Y = 0$ to $Y = H$ ($2.8\text{m}$). At door portal intervals, wall quads are split vertically, terminating at door lintel height ($2.1\text{m}$) to leave open door cutouts. The resulting mesh is validated for watertightness and exported as a binary GLB container.

---

### Category 5: Full-Stack System Architecture & Scalability

#### Q23: Why does MAPORA use a dual database strategy (SQLite and PostgreSQL)?
**Answer:** For enterprise production deployments, MAPORA connects to PostgreSQL for concurrent multi-user transactions, row-level locking, and connection pooling. However, for development, offline site surveys, and oral viva demonstrations where external database servers may be unreachable, MAPORA implements an automated fallback to a local SQLite database (`mapora_dev.db`). The SQLAlchemy ORM abstracts SQL dialect differences, ensuring identical schema creation and query execution across both engines.

#### Q24: How does the frontend handle token expiration during long-running operations?
**Answer:** JWT access tokens have a short lifespan (15 minutes). The frontend API client provides three layers of defense:
1. **Proactive Inspection:** It decodes the JWT payload client-side before sending a request. If the token expires within 30 seconds, it triggers a refresh first.
2. **Single-Flight Refresh Mutex:** If multiple asynchronous requests encounter an expired token concurrently, `refreshAccessToken()` caches the pending refresh promise (`activeRefreshPromise`), ensuring only one network request is made to `/auth/refresh`.
3. **401 Interceptor:** If a request receives an HTTP 401 response, the interceptor catches it, executes token refresh, updates credentials, and replays the original request automatically without failing the user's action.

#### Q25: Why is Trimesh preferred over Blender or Open3D on the backend?
**Answer:** Blender requires a heavyweight external binary installation (>500MB) and headless subprocess spawning, making containerization and cross-platform installation slow and fragile. Open3D is optimized for point clouds, but has heavier C++ dependency chains on Windows. Trimesh is a lightweight, pure-Python and NumPy-based computational geometry library that performs polygon boolean operations, triangulations, and GLB/OBJ serialization quickly with minimal system dependencies.

#### Q26: How does the system handle asynchronous reconstruction jobs when Redis is unavailable?
**Answer:** When Redis and Celery are running, reconstruction tasks are enqueued to a distributed message broker and processed by Celery worker pools. If Redis is unreachable (e.g., local Windows demonstration without Docker), MAPORA's `JobService` gracefully falls back to executing the pipeline in a background Python thread within the FastAPI process. The client polls `/projects/{id}/status` identically in both modes.

---

### Category 6: Security, Reliability & Edge Cases

#### Q27: How does MAPORA protect against unauthorized project access (IDOR attacks)?
**Answer:** Every project access route uses FastAPI dependency injection (`get_authorized_project`). The dependency retrieves the project from the database by ID and verifies that the requesting user is either an `admin` or the `surveyor` who created the project (`project.owner_id == current_user.id`). If a surveyor attempts to access another user’s project ID, the system returns HTTP 403 Forbidden.

#### Q28: How does MAPORA enforce the "Zero Synthetic Fabrication" integrity rule?
**Answer:** In development or sample mode, the application displays clear badges: `ILLUSTRATIVE SAMPLE · NOT GENERATED`. When a user uploads a real video or photos, the viewer *never* substitutes sample apartment geometry if processing fails; instead, it renders an explicit error screen stating that reconstruction geometry is unavailable. In multi-photo mode with only one photo, it renders a 2.5D model with an explicit 45% confidence warning rather than fabricating multi-view triangulation.

#### Q29: What happens if an uploaded video contains no motion (stationary camera)?
**Answer:** Epipolar geometry requires baseline translation ($t \neq 0$). A stationary camera rotating on its optical axis undergoes a pure homography ($x_2 = H x_1$), which has zero baseline ($t = 0$). In this case, 3D triangulation fails because rays are collinear ($0^\circ$ parallax angle). MAPORA’s visual odometry pipeline detects near-zero translation baselines ($\|t\| < \epsilon$), falls back to single-view depth projection, and alerts the user that camera translation is required for full multi-view reconstruction.

#### Q30: How are CAD/BIM exports generated from 2D and 3D data structures?
**Answer:**
- **DXF:** Formatted as standard AutoCAD DXF text entities (`LINE`, `LWPOLYLINE`, `TEXT`) organized into discrete layers (`WALLS`, `DOORS`, `MEASUREMENTS`).
- **PDF:** Generated via vector graphics engines into an architectural sheet with standard margin borders, scale ruler, and title block.
- **SVG:** Structured XML containing `<polygon>`, `<line>`, and `<text>` elements scaled to an architectural canvas.
- **OBJ & GLB:** Generated directly by Trimesh from watertight 3D polygon meshes with embedded vertex normals and materials.

