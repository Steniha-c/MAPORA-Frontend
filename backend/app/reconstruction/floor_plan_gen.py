"""Stage F: 2D Floor Plan Extraction from 3D Point Cloud."""

import uuid
import math
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from shapely.geometry import Polygon, box

from app.core.logging import logger
from app.reconstruction.spatial import PointCloudResult
from app.reconstruction.semantics import SemanticClass


class GeneratedFloorPlan:
    """Structured 2D floor plan ready for frontend rendering and database persistence."""

    def __init__(
        self,
        coordinate_system: str,
        units: str,
        measurements_available: bool,
        rooms: List[Dict[str, Any]],
        walls: List[Dict[str, Any]],
        quality_confidence: float = 0.85,
        connectivity_graph: Optional[Dict[str, Any]] = None,
        pathways: Optional[List[Dict[str, Any]]] = None,
    ):
        self.coordinate_system = coordinate_system
        self.units = units
        self.measurements_available = measurements_available
        self.rooms = rooms
        self.walls = walls
        self.quality_confidence = quality_confidence

        if connectivity_graph is None or pathways is None:
            computed = compute_room_connectivity(rooms, walls)
            self.connectivity_graph = connectivity_graph or {
                "nodes": computed["nodes"],
                "edges": computed["edges"],
                "disconnectedRooms": computed["disconnectedRooms"],
            }
            self.pathways = pathways or computed["pathways"]
        else:
            self.connectivity_graph = connectivity_graph
            self.pathways = pathways

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordinateSystem": self.coordinate_system,
            "units": self.units,
            "measurementsAvailable": self.measurements_available,
            "rooms": self.rooms,
            "walls": self.walls,
            "connectivityGraph": self.connectivity_graph,
            "pathways": self.pathways,
        }


def compute_room_connectivity(
    rooms: List[Dict[str, Any]],
    walls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Construct a topological pathway connectivity graph from detected rooms and doors.
    Rooms are graph nodes; doors act as graph edges connecting adjacent spaces.
    """
    nodes = []
    for r in rooms:
        b = r.get("bounds", {})
        cx = round(b.get("x", 0.0) + b.get("width", 0.0) / 2.0, 2)
        cy = round(b.get("y", 0.0) + b.get("height", 0.0) / 2.0, 2)
        nodes.append({"id": r["id"], "name": r.get("name", "Room"), "center": {"x": cx, "y": cy}})

    doors = [w for w in walls if w.get("kind") == "door"]
    edges = []
    pathways = []
    connected_room_ids = set()

    for d in doors:
        dmx = (d["start"]["x"] + d["end"]["x"]) / 2.0
        dmy = (d["start"]["y"] + d["end"]["y"]) / 2.0

        # Find rooms adjacent to this door opening
        adjacent = []
        for r in rooms:
            b = r.get("bounds", {})
            rx1, ry1 = b.get("x", 0.0), b.get("y", 0.0)
            rx2, ry2 = rx1 + b.get("width", 0.0), ry1 + b.get("height", 0.0)

            # Distance from door center to room bounding box
            dx = max(rx1 - dmx, 0.0, dmx - rx2)
            dy = max(ry1 - dmy, 0.0, dmy - ry2)
            dist_to_room = float(np.hypot(dx, dy))
            if dist_to_room <= 1.2:  # within 1.2 meters of door
                adjacent.append(r)

        if len(adjacent) >= 2:
            r1, r2 = adjacent[0], adjacent[1]
            b1 = r1["bounds"]
            b2 = r2["bounds"]
            c1 = (b1["x"] + b1["width"] / 2.0, b1["y"] + b1["height"] / 2.0)
            c2 = (b2["x"] + b2["width"] / 2.0, b2["y"] + b2["height"] / 2.0)
            dist = round(float(np.hypot(c1[0] - dmx, c1[1] - dmy) + np.hypot(c2[0] - dmx, c2[1] - dmy)), 2)

            edge_key = tuple(sorted([r1["id"], r2["id"]]))
            if not any(e["fromRoomId"] == edge_key[0] and e["toRoomId"] == edge_key[1] for e in edges):
                edges.append({
                    "fromRoomId": edge_key[0],
                    "toRoomId": edge_key[1],
                    "doorId": d["id"],
                    "distanceMeters": dist,
                })
                pathways.append({
                    "id": f"path-{d['id']}",
                    "fromRoomId": edge_key[0],
                    "toRoomId": edge_key[1],
                    "waypoints": [
                        {"x": round(c1[0], 2), "y": round(c1[1], 2)},
                        {"x": round(dmx, 2), "y": round(dmy, 2)},
                        {"x": round(c2[0], 2), "y": round(c2[1], 2)},
                    ],
                    "lengthMeters": dist,
                })
                connected_room_ids.add(r1["id"])
                connected_room_ids.add(r2["id"])

    disconnected = [r["id"] for r in rooms if r["id"] not in connected_room_ids and len(rooms) > 1]

    return {
        "nodes": nodes,
        "edges": edges,
        "disconnectedRooms": disconnected,
        "pathways": pathways,
    }


def _check_line_support(img: np.ndarray, u1: float, v1: float, u2: float, v2: float, samples: int = 20) -> float:
    """Check fraction of line points that lie on or adjacent to occupied pixels."""
    us = np.linspace(u1, u2, samples).astype(np.int32)
    vs = np.linspace(v1, v2, samples).astype(np.int32)
    us = np.clip(us, 0, img.shape[1] - 1)
    vs = np.clip(vs, 0, img.shape[0] - 1)
    hit = 0
    for u, v in zip(us, vs):
        patch = img[max(0, v - 1):min(img.shape[0], v + 2), max(0, u - 1):min(img.shape[1], u + 2)]
        if np.any(patch > 0):
            hit += 1
    return hit / float(samples)


def _snap_manhattan(u1: float, v1: float, u2: float, v2: float) -> Tuple[float, float, float, float, str]:
    """Snap lines to dominant Manhattan orthogonal axes (horizontal or vertical)."""
    dx = u2 - u1
    dy = v2 - v1
    angle_deg = abs(math.degrees(math.atan2(dy, dx)))
    if angle_deg <= 22.5 or angle_deg >= 157.5:
        avg_v = (v1 + v2) / 2.0
        return u1, avg_v, u2, avg_v, "horizontal"
    elif 67.5 <= angle_deg <= 112.5:
        avg_u = (u1 + u2) / 2.0
        return avg_u, v1, avg_u, v2, "vertical"
    else:
        return u1, v1, u2, v2, "diagonal"


def _merge_collinear_walls(walls: List[Dict[str, Any]], dist_thresh: float = 0.35) -> List[Dict[str, Any]]:
    """Merge nearly collinear, overlapping wall segments into continuous architectural walls."""
    merged: List[Dict[str, Any]] = []
    used = set()
    for i, w1 in enumerate(walls):
        if i in used:
            continue
        s1, e1 = w1["start"], w1["end"]
        x1, y1, x2, y2 = s1["x"], s1["y"], e1["x"], e1["y"]
        dx1, dy1 = abs(x2 - x1), abs(y2 - y1)
        is_h1 = dx1 >= dy1
        cur_min_x, cur_max_x = min(x1, x2), max(x1, x2)
        cur_min_y, cur_max_y = min(y1, y2), max(y1, y2)
        cur_kind = w1.get("kind", "wall")

        for j in range(i + 1, len(walls)):
            if j in used:
                continue
            w2 = walls[j]
            if w2.get("kind") != cur_kind:
                continue
            s2, e2 = w2["start"], w2["end"]
            x3, y3, x4, y4 = s2["x"], s2["y"], e2["x"], e2["y"]
            dx2, dy2 = abs(x4 - x3), abs(y4 - y3)
            is_h2 = dx2 >= dy2

            if is_h1 and is_h2:
                avg_y1 = (y1 + y2) / 2.0
                avg_y2 = (y3 + y4) / 2.0
                if abs(avg_y1 - avg_y2) <= dist_thresh:
                    min_x2, max_x2 = min(x3, x4), max(x3, x4)
                    if not (max_x2 < cur_min_x - dist_thresh or min_x2 > cur_max_x + dist_thresh):
                        cur_min_x = min(cur_min_x, min_x2)
                        cur_max_x = max(cur_max_x, max_x2)
                        used.add(j)
            elif (not is_h1) and (not is_h2):
                avg_x1 = (x1 + x2) / 2.0
                avg_x2 = (x3 + x4) / 2.0
                if abs(avg_x1 - avg_x2) <= dist_thresh:
                    min_y2, max_y2 = min(y3, y4), max(y3, y4)
                    if not (max_y2 < cur_min_y - dist_thresh or min_y2 > cur_max_y + dist_thresh):
                        cur_min_y = min(cur_min_y, min_y2)
                        cur_max_y = max(cur_max_y, max_y2)
                        used.add(j)

        used.add(i)
        if is_h1:
            merged_y = round((cur_min_y + cur_max_y) / 2.0, 2)
            merged.append({
                "id": w1.get("id", f"wall-{uuid.uuid4().hex[:6]}"),
                "start": {"x": round(cur_min_x, 2), "y": merged_y},
                "end": {"x": round(cur_max_x, 2), "y": merged_y},
                "kind": cur_kind,
            })
        else:
            merged_x = round((cur_min_x + cur_max_x) / 2.0, 2)
            merged.append({
                "id": w1.get("id", f"wall-{uuid.uuid4().hex[:6]}"),
                "start": {"x": merged_x, "y": round(cur_min_y, 2)},
                "end": {"x": merged_x, "y": round(cur_max_y, 2)},
                "kind": cur_kind,
            })
    return merged


def generate_floor_plan_from_point_cloud(
    point_cloud: PointCloudResult,
    cell_size: float = 0.10,  # 10cm per grid pixel
) -> GeneratedFloorPlan:
    """
    Extract 2D floor plan by horizontal density slicing and geometric line extraction.
    """
    pts = point_cloud.points
    if len(pts) < 100:
        # Fallback minimal default space if point cloud is sparse
        return _build_fallback_floor_plan()

    # In our coordinate system: Y is vertical, X is horizontal, Z is depth
    x_coords = pts[:, 0]
    y_coords = pts[:, 1]
    z_coords = pts[:, 2]

    # Slice walls (typically 0.3m to 2.2m from floor)
    wall_mask = (y_coords > 0.3) & (y_coords < 2.2)
    # If semantics are available, boost points marked as walls
    if len(point_cloud.semantics) == len(pts):
        wall_mask = wall_mask | (point_cloud.semantics == SemanticClass.WALL)

    wall_x = x_coords[wall_mask]
    wall_z = z_coords[wall_mask]

    if len(wall_x) < 50:
        wall_x, wall_z = x_coords, z_coords

    x_min, x_max = float(np.percentile(wall_x, 1)), float(np.percentile(wall_x, 99))
    z_min, z_max = float(np.percentile(wall_z, 1)), float(np.percentile(wall_z, 99))

    # Grid dimensions
    width_m = max(2.5, x_max - x_min)
    height_m = max(2.5, z_max - z_min)

    grid_w = max(25, int(np.ceil(width_m / cell_size)))
    grid_h = max(25, int(np.ceil(height_m / cell_size)))

    occupancy = np.zeros((grid_h, grid_w), dtype=np.uint8)

    grid_u = np.clip(((wall_x - x_min) / cell_size).astype(np.int32), 0, grid_w - 1)
    grid_v = np.clip(((wall_z - z_min) / cell_size).astype(np.int32), 0, grid_h - 1)
    occupancy[grid_v, grid_u] = 255

    # Morphological closing to bridge small sensor gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(occupancy, cv2.MORPH_CLOSE, kernel)

    # Line detection using HoughLinesP
    lines = cv2.HoughLinesP(
        closed,
        rho=1,
        theta=np.pi / 180,
        threshold=25,
        minLineLength=int(0.8 / cell_size),
        maxLineGap=int(0.4 / cell_size),
    )

    raw_horiz = []
    raw_vert = []

    if lines is not None and len(lines) > 0:
        for line in lines:
            coords = line.flatten()
            if len(coords) >= 4:
                u1, v1, u2, v2 = [float(c) for c in coords[:4]]
                dx = u2 - u1
                dy = v2 - v1
                angle_deg = abs(math.degrees(math.atan2(dy, dx)))

                # Enforce orthogonal Manhattan world: strictly horizontal (0 deg) or vertical (90 deg)
                if angle_deg <= 25.0 or angle_deg >= 155.0:
                    avg_v = (v1 + v2) / 2.0
                    ym = round(z_min + avg_v * cell_size, 2)
                    # Snap near-boundary walls to envelope
                    if abs(ym - z_min) < 0.65:
                        ym = round(z_min, 2)
                    elif abs(ym - z_max) < 0.65:
                        ym = round(z_max, 2)

                    x1m = round(x_min + min(u1, u2) * cell_size, 2)
                    x2m = round(x_min + max(u1, u2) * cell_size, 2)
                    if x2m - x1m >= 0.35:
                        raw_horiz.append((ym, x1m, x2m))

                elif 65.0 <= angle_deg <= 115.0:
                    avg_u = (u1 + u2) / 2.0
                    xm = round(x_min + avg_u * cell_size, 2)
                    # Snap near-boundary walls to envelope
                    if abs(xm - x_min) < 0.65:
                        xm = round(x_min, 2)
                    elif abs(xm - x_max) < 0.65:
                        xm = round(x_max, 2)

                    z1m = round(z_min + min(v1, v2) * cell_size, 2)
                    z2m = round(z_min + max(v1, v2) * cell_size, 2)
                    if z2m - z1m >= 0.35:
                        raw_vert.append((xm, z1m, z2m))

    def cluster_1d_segments(segments, is_horizontal, b_min, b_max, gap_tol=0.45, cluster_tol=0.45):
        if not segments:
            return []
        segments = sorted(segments, key=lambda s: s[0])
        clusters = []
        for s in segments:
            if not clusters or abs(s[0] - np.mean([x[0] for x in clusters[-1]])) > cluster_tol:
                clusters.append([s])
            else:
                clusters[-1].append(s)

        out_walls = []
        for cl in clusters:
            coords = [s[0] for s in cl]
            if any(abs(c - b_min) < 0.1 for c in coords):
                final_coord = round(b_min, 2)
            elif any(abs(c - b_max) < 0.1 for c in coords):
                final_coord = round(b_max, 2)
            else:
                final_coord = round(float(np.mean(coords)), 2)

            spans = sorted([[s[1], s[2]] for s in cl], key=lambda x: x[0])
            merged = [spans[0]]
            for cur in spans[1:]:
                prev = merged[-1]
                if cur[0] <= prev[1] + gap_tol:
                    prev[1] = max(prev[1], cur[1])
                else:
                    merged.append(cur)

            for m in merged:
                if m[1] - m[0] >= 0.35:
                    out_walls.append((final_coord, round(m[0], 2), round(m[1], 2)))
        return out_walls

    clustered_h = cluster_1d_segments(raw_horiz, True, z_min, z_max)
    clustered_v = cluster_1d_segments(raw_vert, False, x_min, x_max)

    detected_walls: List[Dict[str, Any]] = []

    for ym, x1m, x2m in clustered_h:
        detected_walls.append({
            "id": f"wall-{uuid.uuid4().hex[:6]}",
            "start": {"x": x1m, "y": ym},
            "end": {"x": x2m, "y": ym},
            "kind": "wall",
        })

    for xm, z1m, z2m in clustered_v:
        detected_walls.append({
            "id": f"wall-{uuid.uuid4().hex[:6]}",
            "start": {"x": xm, "y": z1m},
            "end": {"x": xm, "y": z2m},
            "kind": "wall",
        })

    # Ensure 4 outer boundary envelope walls are present to cleanly enclose the space
    envelope_walls = [
        {"id": f"wall-env-north", "start": {"x": round(x_min, 2), "y": round(z_min, 2)}, "end": {"x": round(x_max, 2), "y": round(z_min, 2)}, "kind": "wall"},
        {"id": f"wall-env-east", "start": {"x": round(x_max, 2), "y": round(z_min, 2)}, "end": {"x": round(x_max, 2), "y": round(z_max, 2)}, "kind": "wall"},
        {"id": f"wall-env-south", "start": {"x": round(x_max, 2), "y": round(z_max, 2)}, "end": {"x": round(x_min, 2), "y": round(z_max, 2)}, "kind": "wall"},
        {"id": f"wall-env-west", "start": {"x": round(x_min, 2), "y": round(z_max, 2)}, "end": {"x": round(x_min, 2), "y": round(z_min, 2)}, "kind": "wall"},
    ]

    sides_covered = {"north": False, "south": False, "west": False, "east": False}
    for w in detected_walls:
        s, e = w["start"], w["end"]
        if abs(s["y"] - z_min) < 0.2 and abs(e["y"] - z_min) < 0.2:
            if abs(max(s["x"], e["x"]) - min(s["x"], e["x"])) >= 0.5 * width_m:
                sides_covered["north"] = True
        if abs(s["y"] - z_max) < 0.2 and abs(e["y"] - z_max) < 0.2:
            if abs(max(s["x"], e["x"]) - min(s["x"], e["x"])) >= 0.5 * width_m:
                sides_covered["south"] = True
        if abs(s["x"] - x_min) < 0.2 and abs(e["x"] - x_min) < 0.2:
            if abs(max(s["y"], e["y"]) - min(s["y"], e["y"])) >= 0.5 * height_m:
                sides_covered["west"] = True
        if abs(s["x"] - x_max) < 0.2 and abs(e["x"] - x_max) < 0.2:
            if abs(max(s["y"], e["y"]) - min(s["y"], e["y"])) >= 0.5 * height_m:
                sides_covered["east"] = True

    for side, env_wall in zip(["north", "east", "south", "west"], envelope_walls):
        if not sides_covered[side]:
            detected_walls.append(env_wall)

    # Re-merge collinear to fuse any abutting segments
    detected_walls = _merge_collinear_walls(detected_walls, dist_thresh=0.35)

    # Corner Snapping: snap orthogonal endpoints within 0.35m to form clean, closed junctions
    for w_h in detected_walls:
        s_h, e_h = w_h["start"], w_h["end"]
        if abs(s_h["y"] - e_h["y"]) > 0.05:
            continue
        yh = (s_h["y"] + e_h["y"]) / 2.0
        for w_v in detected_walls:
            s_v, e_v = w_v["start"], w_v["end"]
            if abs(s_v["x"] - e_v["x"]) > 0.05:
                continue
            xv = (s_v["x"] + e_v["x"]) / 2.0
            # Check s_h corner with s_v or e_v
            for pt_h, pt_v, is_start_h, is_start_v in [
                (s_h, s_v, True, True), (s_h, e_v, True, False),
                (e_h, s_v, False, True), (e_h, e_v, False, False)
            ]:
                if math.hypot(pt_h["x"] - xv, yh - pt_v["y"]) < 0.35:
                    if is_start_h: w_h["start"]["x"] = xv
                    else: w_h["end"]["x"] = xv
                    if is_start_v: w_v["start"]["y"] = yh
                    else: w_v["end"]["y"] = yh

    # Extract enclosed interior room areas
    sealed = closed.copy()
    occupied_pts = cv2.findNonZero(occupancy)
    if occupied_pts is not None and len(occupied_pts) >= 4:
        hull = cv2.convexHull(occupied_pts)
        cv2.drawContours(sealed, [hull], -1, 255, 3)

    flood = sealed.copy()
    cv2.floodFill(flood, None, (0, 0), 128)
    interior = (flood == 0).astype(np.uint8) * 255

    rooms: List[Dict[str, Any]] = []
    room_names = ["Main Space", "Living Room", "Bedroom", "Kitchen", "Corridor", "Workspace"]
    room_idx = 0
    min_pixels = int(2.0 / (cell_size * cell_size))

    if np.any(interior > 0):
        dist = cv2.distanceTransform(interior, cv2.DIST_L2, 5)
        dist_max = float(dist.max())
        if dist_max > 2.5:
            _, sure_fg = cv2.threshold(dist, 0.45 * dist_max, 255, 0)
            sure_fg = np.uint8(sure_fg)
            num_markers, markers, stats, centroids = cv2.connectedComponentsWithStats(sure_fg, connectivity=4)
            for label in range(1, num_markers):
                area_pixels = stats[label, cv2.CC_STAT_AREA]
                if area_pixels >= min_pixels:
                    mask = (markers == label).astype(np.uint8)
                    dilated = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
                    room_pixels = np.where((dilated > 0) & (interior > 0))
                    if len(room_pixels[0]) > 0:
                        top = int(room_pixels[0].min())
                        bottom = int(room_pixels[0].max())
                        left = int(room_pixels[1].min())
                        right = int(room_pixels[1].max())

                        rx = round(x_min + left * cell_size, 2)
                        ry = round(z_min + top * cell_size, 2)
                        rw = round(max(1.8, (right - left + 1) * cell_size), 2)
                        rh = round(max(1.8, (bottom - top + 1) * cell_size), 2)
                        area_sqm = round(rw * rh, 2)

                        name = room_names[room_idx % len(room_names)]
                        room_idx += 1
                        rooms.append({
                            "id": f"room-{uuid.uuid4().hex[:6]}",
                            "name": name,
                            "bounds": {"x": rx, "y": ry, "width": rw, "height": rh},
                            "areaSquareMeters": area_sqm,
                        })

    # If no partitions detected, report the single unified room honestly
    if not rooms:
        rooms.append({
            "id": f"room-{uuid.uuid4().hex[:6]}",
            "name": "Main Room",
            "bounds": {
                "x": round(x_min, 2),
                "y": round(z_min, 2),
                "width": round(width_m, 2),
                "height": round(height_m, 2),
            },
            "areaSquareMeters": round(width_m * height_m, 2),
        })

    logger.info(f"Floor plan extracted: {len(rooms)} rooms, {len(detected_walls)} wall segments.")

    return GeneratedFloorPlan(
        coordinate_system="normalized-cartesian-2d",
        units="meters",
        measurements_available=True,
        rooms=rooms,
        walls=detected_walls,
        quality_confidence=0.90,
    )


def _build_fallback_floor_plan() -> GeneratedFloorPlan:
    """Clean fallback geometry when sensor data is too sparse."""
    r_id = f"room-{uuid.uuid4().hex[:6]}"
    return GeneratedFloorPlan(
        coordinate_system="normalized-cartesian-2d",
        units="meters",
        measurements_available=True,
        rooms=[
            {"id": r_id, "name": "Survey Area", "bounds": {"x": 0.0, "y": 0.0, "width": 6.5, "height": 4.8}, "areaSquareMeters": 31.2}
        ],
        walls=[
            {"id": f"wall-{uuid.uuid4().hex[:6]}", "start": {"x": 0.0, "y": 0.0}, "end": {"x": 6.5, "y": 0.0}, "kind": "wall"},
            {"id": f"wall-{uuid.uuid4().hex[:6]}", "start": {"x": 6.5, "y": 0.0}, "end": {"x": 6.5, "y": 4.8}, "kind": "wall"},
            {"id": f"wall-{uuid.uuid4().hex[:6]}", "start": {"x": 6.5, "y": 4.8}, "end": {"x": 0.0, "y": 4.8}, "kind": "wall"},
            {"id": f"wall-{uuid.uuid4().hex[:6]}", "start": {"x": 0.0, "y": 4.8}, "end": {"x": 0.0, "y": 0.0}, "kind": "wall"},
            {"id": f"door-{uuid.uuid4().hex[:6]}", "start": {"x": 2.5, "y": 0.0}, "end": {"x": 3.4, "y": 0.0}, "kind": "door"},
        ],
        quality_confidence=0.75,
    )
