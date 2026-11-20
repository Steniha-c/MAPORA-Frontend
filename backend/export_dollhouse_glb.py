"""Generate high-fidelity architectural dollhouse GLB replicating reference design."""

import math
import os
import trimesh
from trimesh.visual.material import PBRMaterial

scene = trimesh.Scene()

wall_mat = PBRMaterial(
    name="WallMaterial",
    roughnessFactor=0.78,
    metallicFactor=0.01,
    baseColorFactor=[0.98, 0.98, 0.99, 1.0],
    doubleSided=True,
)
floor_mat = PBRMaterial(
    name="FloorMaterial",
    roughnessFactor=0.88,
    metallicFactor=0.02,
    baseColorFactor=[0.94, 0.95, 0.96, 1.0],
    doubleSided=True,
)
frame_mat = PBRMaterial(
    name="FrameMaterial",
    roughnessFactor=0.60,
    metallicFactor=0.05,
    baseColorFactor=[0.92, 0.93, 0.95, 1.0],
    doubleSided=True,
)

def add_box(center, size, mat, name, rot_y=0.0):
    box = trimesh.creation.box(extents=size)
    if rot_y != 0.0:
        rot = trimesh.transformations.rotation_matrix(rot_y, [0, 1, 0])
        box.apply_transform(rot)
    box.apply_translation(center)
    box.visual.material = mat
    scene.add_geometry(box, node_name=name)

# 1. Base floor slab
add_box([0, -0.04, 0], [11.8, 0.08, 7.8], floor_mat, "Floor Slab")

# 2. Front exterior walls
add_box([-5.5, 0.69, 3.8], [0.6, 1.38, 0.2], wall_mat, "Wall_Front_Left_Post")
add_box([-4.2, 0.19, 3.8], [2.0, 0.38, 0.2], wall_mat, "Window_Sill_Living")
add_box([-4.2, 1.28, 3.8], [2.0, 0.20, 0.2], wall_mat, "Window_Lintel_Living")
add_box([-4.2, 0.73, 3.8], [0.04, 0.90, 0.12], frame_mat, "Window_Mullion_Living")
add_box([-2.5, 0.69, 3.8], [1.4, 1.38, 0.2], wall_mat, "Wall_Front_Left_Return")

add_box([1.1, 0.69, 3.8], [0.6, 1.38, 0.2], wall_mat, "Wall_Front_Right_Post")
add_box([2.2, 0.19, 3.8], [1.6, 0.38, 0.2], wall_mat, "Window_Sill_Bed2")
add_box([2.2, 1.28, 3.8], [1.6, 0.20, 0.2], wall_mat, "Window_Lintel_Bed2")
add_box([2.2, 0.73, 3.8], [0.04, 0.90, 0.12], frame_mat, "Window_Mullion_Bed2")
add_box([3.25, 0.69, 3.8], [0.5, 1.38, 0.2], wall_mat, "Wall_Front_Intermediate")
add_box([4.4, 0.05, 3.8], [1.8, 0.10, 0.2], frame_mat, "Threshold_Sliding_Front")
add_box([4.4, 1.29, 3.8], [1.8, 0.18, 0.2], wall_mat, "Lintel_Sliding_Front")
add_box([3.95, 0.68, 3.8], [0.04, 1.12, 0.12], frame_mat, "Mullion_Sliding_Front_1")
add_box([4.85, 0.68, 3.8], [0.04, 1.12, 0.12], frame_mat, "Mullion_Sliding_Front_2")
add_box([5.55, 0.69, 3.8], [0.5, 1.38, 0.2], wall_mat, "Wall_Front_Right_Post")

# 3. Left exterior walls
add_box([-5.8, 0.69, 3.3], [0.2, 1.38, 1.0], wall_mat, "Wall_Left_Front")
add_box([-5.8, 0.21, 1.9], [0.2, 0.42, 1.8], wall_mat, "Window_Sill_Side")
add_box([-5.8, 1.28, 1.9], [0.2, 0.20, 1.8], wall_mat, "Window_Lintel_Side")
add_box([-5.8, 0.74, 1.9], [0.12, 0.88, 0.04], frame_mat, "Window_Mullion_Side")
add_box([-5.8, 0.69, 0.55], [0.2, 1.38, 0.9], wall_mat, "Wall_Left_Junction")
add_box([-5.8, 0.21, -1.8], [0.2, 0.42, 2.6], wall_mat, "Ribbon_Window_Sill")
add_box([-5.8, 1.28, -1.8], [0.2, 0.20, 2.6], wall_mat, "Ribbon_Window_Lintel")
add_box([-5.8, 0.74, -1.37], [0.12, 0.88, 0.04], frame_mat, "Ribbon_Mullion_1")
add_box([-5.8, 0.74, -2.23], [0.12, 0.88, 0.04], frame_mat, "Ribbon_Mullion_2")
add_box([-5.8, 0.69, -3.45], [0.2, 1.38, 0.7], wall_mat, "Wall_Left_Rear")

# 4. Back exterior walls
add_box([-3.8, 0.69, -3.8], [4.0, 1.38, 0.2], wall_mat, "Wall_Back_Bed1")
add_box([-1.35, 0.69, -3.8], [0.9, 1.38, 0.2], wall_mat, "Wall_Back_Bath_Left")
add_box([-0.4, 0.35, -3.8], [1.0, 0.70, 0.2], wall_mat, "Window_Sill_Bath")
add_box([-0.4, 1.28, -3.8], [1.0, 0.20, 0.2], wall_mat, "Window_Lintel_Bath")
add_box([0.45, 0.69, -3.8], [0.7, 1.38, 0.2], wall_mat, "Wall_Back_Bath_Right")
add_box([3.1, 0.05, -3.8], [3.4, 0.10, 0.2], frame_mat, "Threshold_Master_Back")
add_box([3.1, 1.29, -3.8], [3.4, 0.18, 0.2], wall_mat, "Lintel_Master_Back")
add_box([2.53, 0.69, -3.8], [0.04, 1.18, 0.12], frame_mat, "Mullion_Master_Back_1")
add_box([3.67, 0.69, -3.8], [0.04, 1.18, 0.12], frame_mat, "Mullion_Master_Back_2")
add_box([5.3, 0.69, -3.8], [1.0, 1.38, 0.2], wall_mat, "Wall_Back_Right_Post")

# 5. Right exterior walls
add_box([5.8, 0.69, -3.5], [0.2, 1.38, 0.6], wall_mat, "Wall_Right_Rear")
add_box([5.8, 0.05, -1.9], [0.2, 0.10, 2.6], frame_mat, "Threshold_Master_Right")
add_box([5.8, 1.29, -1.9], [0.2, 0.18, 2.6], wall_mat, "Lintel_Master_Right")
add_box([5.8, 0.69, -1.9], [0.12, 1.18, 0.04], frame_mat, "Mullion_Master_Right")
add_box([5.8, 0.69, -0.3], [0.2, 1.38, 0.6], wall_mat, "Wall_Right_Junction")
add_box([5.8, 0.20, 1.6], [0.2, 0.40, 2.0], wall_mat, "Window_Sill_Bed2_Side")
add_box([5.8, 1.28, 1.6], [0.2, 0.20, 2.0], wall_mat, "Window_Lintel_Bed2_Side")
add_box([5.8, 0.74, 1.6], [0.12, 0.88, 0.04], frame_mat, "Window_Mullion_Bed2_Side")
add_box([5.8, 0.69, 3.2], [0.2, 1.38, 1.2], wall_mat, "Wall_Right_Front")

# 6. Interior partitions
add_box([-4.3, 0.69, 0.1], [3.0, 1.38, 0.2], wall_mat, "Partition_Bed1_Living")
add_box([-2.35, 1.28, 0.1], [0.9, 0.20, 0.2], wall_mat, "Door_Lintel_Living_Bed1")
add_box([-1.85, 0.69, 0.1], [0.1, 1.38, 0.2], wall_mat, "Partition_Junction_Bed1")

add_box([-1.8, 0.69, 3.4], [0.2, 1.38, 0.8], wall_mat, "Partition_Hall_Living_Front")
add_box([-1.8, 1.28, 2.5], [0.2, 0.20, 1.0], wall_mat, "Door_Lintel_Living")
add_box([-1.8, 0.69, 1.05], [0.2, 1.38, 1.9], wall_mat, "Partition_Hall_Living_Mid")
add_box([-1.8, 0.69, -0.7], [0.2, 1.38, 1.6], wall_mat, "Partition_Hall_Bed1_1")
add_box([-1.8, 1.28, -1.95], [0.2, 0.20, 0.9], wall_mat, "Door_Lintel_Bed1")
add_box([-1.8, 0.69, -3.1], [0.2, 1.38, 1.4], wall_mat, "Partition_Hall_Bed1_2")

add_box([-1.45, 0.69, -0.6], [0.7, 1.38, 0.2], wall_mat, "Partition_Bath_Front_1")
add_box([-0.65, 1.28, -0.6], [0.9, 0.20, 0.2], wall_mat, "Door_Lintel_Bath")
add_box([0.3, 0.69, -0.6], [1.0, 1.38, 0.2], wall_mat, "Partition_Bath_Front_2")
add_box([-0.3, 0.69, -2.2], [0.2, 1.38, 3.2], wall_mat, "Partition_Bath_Dividing")

add_box([0.8, 0.69, 3.4], [0.2, 1.38, 0.8], wall_mat, "Partition_Hall_Bed2_Front")
add_box([0.8, 1.28, 2.5], [0.2, 0.20, 1.0], wall_mat, "Door_Lintel_Bed2")
add_box([0.8, 0.69, 1.0], [0.2, 1.38, 2.0], wall_mat, "Partition_Hall_Bed2_Mid")
add_box([0.8, 0.69, -0.9], [0.2, 1.38, 1.8], wall_mat, "Partition_Hall_Master_1")
add_box([0.8, 1.28, -2.25], [0.2, 0.20, 0.9], wall_mat, "Door_Lintel_Master")
add_box([0.8, 0.69, -3.25], [0.2, 1.38, 1.1], wall_mat, "Partition_Hall_Master_2")

add_box([3.3, 0.69, 0.0], [5.0, 1.38, 0.2], wall_mat, "Partition_Bed2_Master")

# 7. Structural Columns
add_box([-2.05, 0.70, 0.35], [0.38, 1.40, 0.38], wall_mat, "Column_Bed1")
add_box([-0.45, 0.70, -2.4], [0.48, 1.40, 0.48], wall_mat, "Column_Bath_ServiceDuct")
add_box([2.2, 0.70, 0.24], [0.42, 1.40, 0.42], wall_mat, "Column_Bed2_Pilaster")

# 8. Open Door Leaves
def add_door_leaf(hinge, size, angle, name):
    door = trimesh.creation.box(extents=size)
    door.apply_translation([size[0] / 2.0, 0, 0])
    rot = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
    door.apply_transform(rot)
    door.apply_translation(hinge)
    door.visual.material = wall_mat
    scene.add_geometry(door, node_name=name)

add_door_leaf([-1.8, 0.59, 2.05], [0.82, 1.18, 0.035], math.pi * 0.22, "DoorLeaf_Living")
add_door_leaf([0.8, 0.59, 2.05], [0.82, 1.18, 0.035], -math.pi * 0.22, "DoorLeaf_Bed2")
add_door_leaf([-2.8, 0.59, 0.1], [0.82, 1.18, 0.035], math.pi * 0.25, "DoorLeaf_Bed1")

out_dir = "storage_data/models/sample-apartment"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "scene.glb")
glb_bytes = trimesh.exchange.gltf.export_glb(scene, include_normals=True)
with open(out_path, "wb") as f:
    f.write(glb_bytes)

print(f"Generated sample dollhouse GLB at {out_path}: {len(glb_bytes)} bytes, {len(scene.geometry)} geometries")
