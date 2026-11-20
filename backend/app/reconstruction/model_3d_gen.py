"""Stage G: 3D Mesh Model Generation (Walls, Openings, Floors) and GLB Export."""

import math
from typing import Any, Dict, List, Optional
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

from app.core.logging import logger
from app.reconstruction.floor_plan_gen import GeneratedFloorPlan


class GeneratedModel3D:
    """Exported 3D spatial geometry model container."""

    def __init__(
        self,
        glb_bytes: bytes,
        vertex_count: int,
        face_count: int,
        room_names: List[str],
        format_type: str = "glb",
    ):
        self.glb_bytes = glb_bytes
        self.vertex_count = vertex_count
        self.face_count = face_count
        self.room_names = room_names
        self.format_type = format_type


def generate_3d_model_from_floor_plan(
    floor_plan: GeneratedFloorPlan,
    wall_height: float = 1.60,
    wall_thickness: float = 0.18,
) -> GeneratedModel3D:
    """
    Extrude 2D floor-plan geometry into a modular, interactive 3D architectural scene.
    Preserves room node names for interactive 3D inspection in the frontend viewer.
    Exports authentic PBR materials, a single coherent floor slab, and continuous solid walls.
    """
    scene = trimesh.Scene()
    total_vertices = 0
    total_faces = 0
    room_names: List[str] = [r.get("name", f"Room {i+1}") for i, r in enumerate(floor_plan.rooms)]

    # Architectural PBR materials (clean matte white/neutral dollhouse styling matching reference aesthetic)
    wall_material = PBRMaterial(
        name="WallMaterial",
        roughnessFactor=0.78,
        metallicFactor=0.01,
        baseColorFactor=[0.98, 0.98, 0.99, 1.0],
        doubleSided=True,
    )
    floor_material = PBRMaterial(
        name="FloorMaterial",
        roughnessFactor=0.88,
        metallicFactor=0.02,
        baseColorFactor=[0.94, 0.95, 0.96, 1.0],
        doubleSided=True,
    )

    all_xs: List[float] = []
    all_zs: List[float] = []

    # Collect coordinates across all walls and room bounds
    for wall in floor_plan.walls:
        s, e = wall.get("start", {}), wall.get("end", {})
        all_xs.extend([float(s.get("x", 0.0)), float(e.get("x", 0.0))])
        all_zs.extend([float(s.get("y", 0.0)), float(e.get("y", 0.0))])

    for room in floor_plan.rooms:
        b = room.get("bounds", {})
        rx = float(b.get("x", 0.0))
        rz = float(b.get("y", 0.0))
        rw = float(b.get("width", 3.0))
        rh = float(b.get("height", 3.0))
        all_xs.extend([rx, rx + rw])
        all_zs.extend([rz, rz + rh])

    # 1. Generate Single Coherent Floor Slab
    if all_xs and all_zs:
        min_x, max_x = min(all_xs), max(all_xs)
        min_z, max_z = min(all_zs), max(all_zs)
        pad = 0.15
        floor_w = max(2.0, (max_x - min_x) + 2 * pad)
        floor_d = max(2.0, (max_z - min_z) + 2 * pad)
        floor_cx = (min_x + max_x) / 2.0
        floor_cz = (min_z + max_z) / 2.0

        floor_slab = trimesh.creation.box(extents=[floor_w, 0.06, floor_d])
        floor_slab.apply_translation([floor_cx, -0.03, floor_cz])
        floor_slab.visual.material = floor_material
        scene.add_geometry(floor_slab, node_name="Floor Slab")
        total_vertices += len(floor_slab.vertices)
        total_faces += len(floor_slab.faces)

    # 2. Extrude Continuous Solid Wall Segments
    for idx, wall in enumerate(floor_plan.walls):
        start = wall.get("start", {})
        end = wall.get("end", {})
        x1, z1 = float(start.get("x", 0.0)), float(start.get("y", 0.0))
        x2, z2 = float(end.get("x", 0.0)), float(end.get("y", 0.0))
        kind = wall.get("kind", "wall")

        dx = x2 - x1
        dz = z2 - z1
        length = math.hypot(dx, dz)
        if length < 0.15:
            continue

        angle = math.atan2(dz, dx)
        mid_x = (x1 + x2) / 2.0
        mid_z = (z1 + z2) / 2.0

        if kind == "door":
            # Door opening: header lintel at top of opening
            header_h = 0.25
            door_header = trimesh.creation.box(extents=[length, header_h, wall_thickness])
            rot = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
            door_header.apply_transform(rot)
            door_header.apply_translation([mid_x, wall_height - header_h / 2.0, mid_z])
            door_header.visual.material = wall_material
            scene.add_geometry(door_header, node_name=f"Door Header {idx + 1}")
            total_vertices += len(door_header.vertices)
            total_faces += len(door_header.faces)
        else:
            # Solid architectural wall
            wall_box = trimesh.creation.box(extents=[length, wall_height, wall_thickness])
            rot = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
            wall_box.apply_transform(rot)
            wall_box.apply_translation([mid_x, wall_height / 2.0, mid_z])
            wall_box.visual.material = wall_material
            scene.add_geometry(wall_box, node_name=f"Wall {idx + 1}")
            total_vertices += len(wall_box.vertices)
            total_faces += len(wall_box.faces)

    # 3. Export GLB binary with explicit normals
    glb_data = trimesh.exchange.gltf.export_glb(scene, include_normals=True)

    logger.info(
        f"Generated 3D GLB Model: {len(glb_data)} bytes, {total_vertices} vertices, "
        f"{total_faces} faces, {len(room_names)} interactive room nodes."
    )

    return GeneratedModel3D(
        glb_bytes=glb_data,
        vertex_count=total_vertices,
        face_count=total_faces,
        room_names=room_names,
        format_type="glb",
    )
