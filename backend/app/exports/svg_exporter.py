"""Export 2D Floor Plan to Scalable Vector Graphics (SVG)."""

import io
from typing import Any, Dict
import svgwrite


def export_floor_plan_to_svg(floor_plan_data: Dict[str, Any], title: str = "Floor Plan") -> bytes:
    """
    Generate clean, architectural vector SVG drawing of rooms, walls, and openings.
    """
    rooms = floor_plan_data.get("rooms", [])
    walls = floor_plan_data.get("walls", [])

    # Calculate bounding box of all elements to set SVG viewBox
    min_x, max_x = 0.0, 10.0
    min_y, max_y = 0.0, 10.0

    all_x = []
    all_y = []

    for r in rooms:
        b = r.get("bounds", {})
        rx = b.get("x", 0.0)
        ry = b.get("y", 0.0)
        rw = b.get("width", 1.0)
        rh = b.get("height", 1.0)
        all_x.extend([rx, rx + rw])
        all_y.extend([ry, ry + rh])

    for w in walls:
        all_x.extend([w.get("start", {}).get("x", 0.0), w.get("end", {}).get("x", 0.0)])
        all_y.extend([w.get("start", {}).get("y", 0.0), w.get("end", {}).get("y", 0.0)])

    if all_x and all_y:
        min_x = min(all_x) - 1.0
        max_x = max(all_x) + 1.0
        min_y = min(all_y) - 1.0
        max_y = max(all_y) + 1.0

    width = max_x - min_x
    height = max_y - min_y
    scale = 60.0  # 60 pixels per meter

    svg_w = max(400, int(width * scale))
    svg_h = max(300, int(height * scale))

    output = io.StringIO()
    dwg = svgwrite.Drawing(size=(f"{svg_w}px", f"{svg_h}px"), profile="full")
    dwg.viewbox(min_x * scale, min_y * scale, width * scale, height * scale)

    # Styles
    dwg.defs.add(dwg.style("""
        .background { fill: #101114; }
        .room-fill { fill: #1a1c22; stroke: #2a2d36; stroke-width: 1; }
        .room-text { font-family: 'Inter', sans-serif; font-size: 14px; fill: #e5e7eb; text-anchor: middle; }
        .room-subtext { font-family: 'Inter', sans-serif; font-size: 10px; fill: #9ca3af; text-anchor: middle; }
        .wall-line { stroke: #f3f4f6; stroke-width: 6; stroke-linecap: round; }
        .door-line { stroke: #f97316; stroke-width: 3; stroke-dasharray: 4,4; }
        .title-text { font-family: 'Inter', sans-serif; font-size: 16px; font-weight: bold; fill: #ffffff; }
    """))

    # Dark architectural background
    dwg.add(dwg.rect(insert=(min_x * scale, min_y * scale), size=(width * scale, height * scale), class_="background"))

    # 1. Render Rooms
    for r in rooms:
        b = r.get("bounds", {})
        rx = b.get("x", 0.0) * scale
        ry = b.get("y", 0.0) * scale
        rw = b.get("width", 1.0) * scale
        rh = b.get("height", 1.0) * scale
        name = r.get("name", "Room")
        area = r.get("areaSquareMeters")

        dwg.add(dwg.rect(insert=(rx, ry), size=(rw, rh), rx=4, ry=4, class_="room-fill"))

        # Center labels
        cx = rx + rw / 2.0
        cy = ry + rh / 2.0
        dwg.add(dwg.text(name, insert=(cx, cy - 4), class_="room-text"))
        if area is not None:
            dwg.add(dwg.text(f"{area:.1f} m²", insert=(cx, cy + 12), class_="room-subtext"))

    # 2. Render Walls and Openings
    for w in walls:
        start = w.get("start", {})
        end = w.get("end", {})
        x1 = start.get("x", 0.0) * scale
        y1 = start.get("y", 0.0) * scale
        x2 = end.get("x", 0.0) * scale
        y2 = end.get("y", 0.0) * scale
        kind = w.get("kind", "wall")

        css_class = "door-line" if kind == "door" else "wall-line"
        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), class_=css_class))

    # Architectural title watermark
    dwg.add(dwg.text(f"MAPORA Spatial Map — {title}", insert=(min_x * scale + 20, min_y * scale + 30), class_="title-text"))

    dwg.write(output)
    return output.getvalue().encode("utf-8")
