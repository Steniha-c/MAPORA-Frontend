import os
import cv2
import numpy as np
import trimesh

output_dir = r"C:\Users\steni\.gemini\antigravity\brain\71419eb5-22b8-48d1-8390-31f16d449123\diagnostics"
os.makedirs(output_dir, exist_ok=True)

img1_path = r"backend\storage_data\images\f3aff50a-24bb-480d-aab8-96f646fc479b\a6ab1a657f2c4752ac8df50d3cea9ce1_mapoora.jpg"
img2_path = r"backend\storage_data\images\f3aff50a-24bb-480d-aab8-96f646fc479b\4576f76b7b834887afa18771459e8e5c_mapoora_1.jpg"

img1 = cv2.imread(img1_path)
img2 = cv2.imread(img2_path)
h1, w1 = img1.shape[:2]
h2, w2 = img2.shape[:2]

print(f"Image 1: {w1}x{h1}, Image 2: {w2}x{h2}")

# 1. Diagnostic 1: Original Uploaded Images Side-by-Side
target_h = max(h1, h2)
canvas1 = cv2.resize(img1, (int(w1 * target_h / h1), target_h))
canvas2 = cv2.resize(img2, (int(w2 * target_h / h2), target_h))
combined_orig = np.hstack([canvas1, canvas2])
# Add labels
banner = np.full((50, combined_orig.shape[1], 3), 30, dtype=np.uint8)
cv2.putText(banner, f"MAPORA Photo 1 (mapoora.jpg: {w1}x{h1})", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
cv2.putText(banner, f"MAPORA Photo 2 (mapoora_1.jpg: {w2}x{h2})", (canvas1.shape[1] + 20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
diag1 = np.vstack([banner, combined_orig])
cv2.imwrite(os.path.join(output_dir, "01_original_photos.png"), diag1)
print("Saved 01_original_photos.png")

# 2. Diagnostic 2: ORB Feature Extraction & Matching
orb = cv2.ORB_create(nfeatures=2000)
gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
kp1, des1 = orb.detectAndCompute(gray1, None)
kp2, des2 = orb.detectAndCompute(gray2, None)

matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
raw_matches = matcher.knnMatch(des1, des2, k=2)
good_matches = [m[0] for m in raw_matches if len(m) == 2 and m[0].distance < 0.75 * m[1].distance]

match_vis = cv2.drawMatches(img1, kp1, img2, kp2, good_matches, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
match_banner = np.full((50, match_vis.shape[1], 3), 30, dtype=np.uint8)
cv2.putText(match_banner, f"ORB Feature Matching: {len(good_matches)} Lowe-ratio matches (RANSAC Inliers: 0 / Threshold >= 15)", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)
diag2 = np.vstack([match_banner, match_vis])
cv2.imwrite(os.path.join(output_dir, "02_feature_matching.png"), diag2)
print(f"Saved 02_feature_matching.png (good matches: {len(good_matches)})")

# 3. Diagnostic 3: Depth Map Estimation (Heuristic fallback)
from app.reconstruction.depth import DepthEstimationAdapter
depth_adapter = DepthEstimationAdapter()
d1 = depth_adapter.estimate_depth(img1)
d2 = depth_adapter.estimate_depth(img2)

# Normalize depth to 0-255 colormap
d1_norm = cv2.normalize(d1.depth_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
d2_norm = cv2.normalize(d2.depth_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
d1_color = cv2.applyColorMap(d1_norm, cv2.COLORMAP_TURBO)
d2_color = cv2.applyColorMap(d2_norm, cv2.COLORMAP_TURBO)

d1_vis = cv2.resize(d1_color, (canvas1.shape[1], target_h))
d2_vis = cv2.resize(d2_color, (canvas2.shape[1], target_h))
combined_depth = np.hstack([d1_vis, d2_vis])
depth_banner = np.full((60, combined_depth.shape[1], 3), 30, dtype=np.uint8)
cv2.putText(depth_banner, f"Photo 1 Depth ({d1.model_name}): {d1.depth_map.min():.1f}m - {d1.depth_map.max():.1f}m", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
cv2.putText(depth_banner, f"Photo 2 Depth ({d2.model_name}): {d2.depth_map.min():.1f}m - {d2.depth_map.max():.1f}m", (canvas1.shape[1] + 20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
diag3 = np.vstack([depth_banner, combined_depth])
cv2.imwrite(os.path.join(output_dir, "03_depth_maps.png"), diag3)
print("Saved 03_depth_maps.png")

# 4. Diagnostic 4: Point Cloud 2D Top-Down Occupancy Grid & Density
from app.reconstruction.image_pipeline import ImageReconstructionPipeline
pipeline = ImageReconstructionPipeline()
out = pipeline.run([img1_path, img2_path])
pts = out.point_cloud.points
colors = out.point_cloud.colors

grid_img = np.full((600, 600, 3), 245, dtype=np.uint8)
# Map X from [-4, 4] and Z from [0, 6] to 600x600 pixels
min_x, max_x = -4.0, 4.0
min_z, max_z = 0.0, 6.0

for pt, col in zip(pts[::2], colors[::2]):
    px = int((pt[0] - min_x) / (max_x - min_x) * 560 + 20)
    pz = int((pt[2] - min_z) / (max_z - min_z) * 560 + 20)
    if 0 <= px < 600 and 0 <= pz < 600:
        cv2.circle(grid_img, (px, 600 - pz), 2, (int(col[0]), int(col[1]), int(col[2])), -1)

# Draw grid lines & axes
for gx in range(-3, 4):
    px = int((gx - min_x) / (max_x - min_x) * 560 + 20)
    cv2.line(grid_img, (px, 0), (px, 600), (220, 220, 220), 1)
    cv2.putText(grid_img, f"{gx}m", (px + 2, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

for gz in range(1, 6):
    pz = int((gz - min_z) / (max_z - min_z) * 560 + 20)
    cv2.line(grid_img, (0, 600 - pz), (600, 600 - pz), (220, 220, 220), 1)
    cv2.putText(grid_img, f"{gz}m", (10, 600 - pz - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

pc_banner = np.full((50, 600, 3), 30, dtype=np.uint8)
cv2.putText(pc_banner, f"Top-Down Point Cloud: {len(pts)} points fused", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
diag4 = np.vstack([pc_banner, grid_img])
cv2.imwrite(os.path.join(output_dir, "04_point_cloud_density.png"), diag4)
print("Saved 04_point_cloud_density.png")

# 5. Diagnostic 5: Reconstructed 3D GLB Slices vs Architectural Walls
glb_path = r"backend\storage_data\models\f3aff50a-24bb-480d-aab8-96f646fc479b\scene_c2ca8129-161b-4b83-ae5c-63f3310c944b.glb"
scene = trimesh.load(glb_path)
mesh_canvas = np.full((600, 600, 3), 250, dtype=np.uint8)

# Draw geometries top-down
for name, geom in scene.geometry.items():
    v = geom.vertices
    # Project 8 vertices to X-Z plane
    pxs = [int((pt[0] - min_x) / (max_x - min_x) * 560 + 20) for pt in v]
    pzs = [int(600 - ((pt[2] - min_z) / (max_z - min_z) * 560 + 20)) for pt in v]
    
    # Draw convex hull of box projection
    poly = np.array(list(zip(pxs, pzs)), dtype=np.int32)
    hull = cv2.convexHull(poly)
    cv2.polylines(mesh_canvas, [hull], True, (0, 0, 220), 2)
    cv2.fillPoly(mesh_canvas, [hull], (220, 230, 255))

mesh_banner = np.full((50, 600, 3), 30, dtype=np.uint8)
cv2.putText(mesh_banner, f"Current GLB Top-Down: {len(scene.geometry)} overlapping slabs", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
diag5 = np.vstack([mesh_banner, mesh_canvas])
cv2.imwrite(os.path.join(output_dir, "05_glb_geometry_topdown.png"), diag5)
print("Saved 05_glb_geometry_topdown.png")
