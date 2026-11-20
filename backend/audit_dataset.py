import os
import glob
import cv2
import numpy as np
import json
import sqlite3

conn = sqlite3.connect('backend/mapora_dev.db')
cursor = conn.cursor()

print("================ DATASET AUDIT ================")

# 1. Projects and their input modalities
cursor.execute("SELECT id, name, input_type, duration, status FROM projects")
projects = cursor.fetchall()
print(f"Total projects in database: {len(projects)}")
for p in projects:
    print(f"  Project {p[0]}: Name='{p[1]}', input_type={p[2]}, duration='{p[3]}', status={p[4]}")

# 2. Uploaded Images Analysis
cursor.execute("SELECT id, project_id, original_filename, storage_key, width, height, file_size_bytes FROM image_uploads")
image_rows = cursor.fetchall()
print(f"\nTotal image uploads in database: {len(image_rows)}")

project_images = {}
for row in image_rows:
    img_id, proj_id, orig_name, skey, w, h, size = row
    disk_path = os.path.join("backend", "storage_data", skey)
    if proj_id not in project_images:
        project_images[proj_id] = []
    project_images[proj_id].append({
        "id": img_id,
        "name": orig_name,
        "path": disk_path,
        "width": w,
        "height": h,
        "size_kb": round(size / 1024, 2) if size else 0
    })

# Check physical existence and quality of images
orb = cv2.ORB_create(nfeatures=1500)
matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

for proj_id, imgs in project_images.items():
    print(f"\n--- Project {proj_id} ({len(imgs)} images) ---")
    loaded_imgs = []
    for info in imgs:
        path = info["path"]
        exists = os.path.exists(path)
        if exists:
            img = cv2.imread(path)
            if img is not None:
                h, w = img.shape[:2]
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                mean_brightness = float(np.mean(gray))
                kp, des = orb.detectAndCompute(gray, None)
                n_kp = len(kp) if kp else 0
                print(f"  Image '{info['name']}': Res={w}x{h}, Blur={blur_var:.1f}, Brightness={mean_brightness:.1f}, Keypoints={n_kp}")
                loaded_imgs.append((info['name'], img, kp, des))
            else:
                print(f"  Image '{info['name']}': FAILED TO READ")
        else:
            print(f"  Image '{info['name']}': FILE MISSING at {path}")

    # Pairwise feature matching
    if len(loaded_imgs) >= 2:
        for i in range(len(loaded_imgs)):
            for j in range(i + 1, len(loaded_imgs)):
                name1, img1, kp1, des1 = loaded_imgs[i]
                name2, img2, kp2, des2 = loaded_imgs[j]
                if des1 is not None and des2 is not None and len(des1) >= 10 and len(des2) >= 10:
                    raw_matches = matcher.knnMatch(des1, des2, k=2)
                    good_matches = [m[0] for m in raw_matches if len(m) == 2 and m[0].distance < 0.75 * m[1].distance]
                    inliers = 0
                    if len(good_matches) >= 8:
                        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
                        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
                        K = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype=np.float64)
                        E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=2.0)
                        inliers = int(np.sum(mask)) if mask is not None else 0
                    print(f"    Pair ({name1} <-> {name2}): Good matches={len(good_matches)}, RANSAC Inliers={inliers}")
                else:
                    print(f"    Pair ({name1} <-> {name2}): Descriptors insufficient")

# 3. Search for Ground-Truth Data
print("\n--- Ground Truth Search ---")
gt_patterns = ["*gt*", "*ground_truth*", "*poses*", "*depth*.png", "*depth*.npy", "*.depth", "*trajectory*"]
found_gt = []
for p in gt_patterns:
    found_gt.extend(glob.glob(f"**/{p}", recursive=True))
print(f"Ground truth files found: {found_gt}")
