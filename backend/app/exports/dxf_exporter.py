"""Export 2D Floor Plan to AutoCAD DXF format."""

import io
from typing import Any, Dict
import ezdxf


def export_floor_plan_to_dxf(floor_plan_data: Dict[str, Any]) -> bytes:
    """
    Generate CAD DXF drawing with distinct layers for WALLS, DOORS, and ROOM_LABELS.
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Create CAD Layers
    doc.layers.add("WALLS", color=7)        # Standard white/black
    doc.layers.add("DOORS", color=1)        # Red
    doc.layers.add("ROOM_LABELS", color=3)  # Green

    rooms = floor_plan_data.get("rooms", [])
    walls = floor_plan_data.get("walls", [])

    # 1. Export Wall and Door Segments
    for w in walls:
        start = w.get("start", {})
        end = w.get("end", {})
        x1 = float(start.get("x", 0.0))
        y1 = float(start.get("y", 0.0))
        x2 = float(end.get("x", 0.0))
        y2 = float(end.get("y", 0.0))
        kind = w.get("kind", "wall")

        layer = "DOORS" if kind == "door" else "WALLS"
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})

    # 2. Export Rooms as polylines and text labels
    for r in rooms:
        b = r.get("bounds", {})
        rx = float(b.get("x", 0.0))
        ry = float(b.get("y", 0.0))
        rw = float(b.get("width", 1.0))
        rh = float(b.get("height", 1.0))
        name = r.get("name", "Room")

        # Room boundary polyline
        points = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh), (rx, ry)]
        msp.add_lwpolyline(points, dxfattribs={"layer": "WALLS"})

        # Room label text
        cx = rx + rw / 2.0
        cy = ry + rh / 2.0
        msp.add_text(
            name,
            dxfattribs={"layer": "ROOM_LABELS", "height": 0.25}
        ).set_placement((cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    buffer = io.StringIO()
    doc.write(buffer)
    return buffer.getvalue().encode("utf-8")
