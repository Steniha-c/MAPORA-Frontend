"""Stage G: 3D Mesh Model Generation (Walls, Openings, Floors) and GLB Export."""

import math
from typing import Any, Dict, List, Optional
import numpy as np
import trimesh

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
    wall_height: float = 2.60,
    wall_thickness: float = 0.15,
) -> GeneratedModel3D:
    """
    Extrude 2D floor-plan geometry into a modular, interactive 3D architectural scene.
    Preserves room node names for interactive 3D inspection in the frontend viewer.
    """
    scene = trimesh.Scene()
    total_vertices = 0
    total_faces = 0
    room_names: List[str] = []

    # 1. Generate Rooms and Floor Slabs
    for idx, room in enumerate(floor_plan.rooms):
        r_name = room.get("name", f"Room {idx + 1}")
        room_names.append(r_name)
        bounds = room.get("bounds", {})
        rx = bounds.get("x", 0.0)
        rz = bounds.get("y", 0.0)  # 2D y maps to 3D z
        rw = bounds.get("width", 3.0)
        rh = bounds.get("height", 3.0)

        # Floor slab
        floor_box = trimesh.creation.box(extents=[rw, 0.04, rh])
        # Position center: Y=-0.02, X=rx + rw/2, Z=rz + rh/2
        floor_box.apply_translation([rx + rw / 2.0, -0.02, rz + rh / 2.0])
        # Floor color (warm architectural slate)
        floor_box.visual.vertex_colors = [50, 52, 58, 255]

        node_name = f"{r_name}"
        scene.add_geometry(floor_box, node_name=node_name)
        total_vertices += len(floor_box.vertices)
        total_faces += len(floor_box.faces)

    # 2. Extrude Wall Segments
    for idx, wall in enumerate(floor_plan.walls):
        start = wall.get("start", {})
        end = wall.get("end", {})
        x1, z1 = start.get("x", 0.0), start.get("y", 0.0)
        x2, z2 = end.get("x", 0.0), end.get("y", 0.0)
        kind = wall.get("kind", "wall")

        dx = x2 - x1
        dz = z2 - z1
        length = math.hypot(dx, dz)
        if length < 0.1:
            continue

        angle = math.atan2(dz, dx)
        mid_x = (x1 + x2) / 2.0
        mid_z = (z1 + z2) / 2.0

        if kind == "door":
            # Door opening: header wall above door frame (from 2.0m to 2.6m)
            header_h = 0.60
            door_header = trimesh.creation.box(extents=[length, header_h, wall_thickness])
            # Rotate around Y axis
            rot = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
            door_header.apply_transform(rot)
            # Center vertically at 2.0 + 0.3 = 2.3m
            door_header.apply_translation([mid_x, 2.30, mid_z])
            door_header.visual.vertex_colors = [120, 125, 135, 255]
            scene.add_geometry(door_header, node_name=f"Door Header {idx + 1}")
            total_vertices += len(door_header.vertices)
            total_faces += len(door_header.faces)
        else:
            # Solid architectural wall
            wall_box = trimesh.creation.box(extents=[length, wall_height, wall_thickness])
            rot = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
            wall_box.apply_transform(rot)
            wall_box.apply_translation([mid_x, wall_height / 2.0, mid_z])
            # Architectural off-white wall color
            wall_box.visual.vertex_colors = [215, 218, 224, 255]
            scene.add_geometry(wall_box, node_name=f"Wall {idx + 1}")
            total_vertices += len(wall_box.vertices)
            total_faces += len(wall_box.faces)

    # 3. Export GLB binary
    glb_data = trimesh.exchange.gltf.export_glb(scene)

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
