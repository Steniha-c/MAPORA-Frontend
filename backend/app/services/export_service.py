"""Export management and dispatch service."""

import io
from typing import Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.export import ExportRecord
from app.models.geometry import FloorPlan, Model3D
from app.models.project import Project
from app.models.user import User
from app.storage.provider import get_storage
from app.exports.svg_exporter import export_floor_plan_to_svg
from app.exports.pdf_exporter import export_floor_plan_to_pdf
from app.exports.dxf_exporter import export_floor_plan_to_dxf


class ExportService:
    """Service generating and persisting architectural export documents."""

    @staticmethod
    def generate_and_save_export(
        db: Session,
        project: Project,
        user: User,
        export_format: str,
    ) -> Tuple[ExportRecord, bytes]:
        fmt = export_format.lower().strip()
        storage = get_storage()

        plan = db.scalar(
            select(FloorPlan).where(
                FloorPlan.project_id == project.id,
                FloorPlan.is_active.is_(True),
            )
        )
        if not plan:
            raise ValueError(f"No active floor plan available for project '{project.name}' to export.")

        plan_dict = {
            "coordinateSystem": plan.coordinate_system,
            "units": plan.units,
            "rooms": [
                {
                    "id": r.id,
                    "name": r.name,
                    "bounds": {"x": r.bounds_x, "y": r.bounds_y, "width": r.bounds_width, "height": r.bounds_height},
                    "areaSquareMeters": r.area_sqm,
                }
                for r in plan.rooms
            ],
            "walls": [
                {
                    "id": w.id,
                    "start": {"x": w.start_x, "y": w.start_y},
                    "end": {"x": w.end_x, "y": w.end_y},
                    "kind": w.kind,
                }
                for w in plan.walls
            ],
        }

        if fmt == "svg":
            file_bytes = export_floor_plan_to_svg(plan_dict, title=project.name)
            mime_type = "image/svg+xml"
            ext = "svg"
        elif fmt == "pdf":
            file_bytes = export_floor_plan_to_pdf(
                plan_dict, project_name=project.name, project_location=project.location
            )
            mime_type = "application/pdf"
            ext = "pdf"
        elif fmt == "dxf":
            file_bytes = export_floor_plan_to_dxf(plan_dict)
            mime_type = "application/dxf"
            ext = "dxf"
        elif fmt in ["glb", "gltf"]:
            model = db.scalar(
                select(Model3D).where(Model3D.project_id == project.id).order_by(Model3D.created_at.desc())
            )
            if not model:
                raise ValueError("No 3D GLB model has been generated for this project yet.")
            with storage.open(model.storage_key) as f:
                file_bytes = f.read()
            mime_type = "model/gltf-binary"
            ext = "glb"
        else:
            raise ValueError(f"Unsupported export format '{export_format}'. Supported: svg, pdf, dxf, glb.")

        filename = f"{project.name.replace(' ', '_').lower()}_{fmt}.{ext}"
        storage_key = f"exports/{project.id}/{uuid.uuid4().hex}_{filename}"

        bio = io.BytesIO(file_bytes)
        storage.save(bio, storage_key, content_type=mime_type)

        record = ExportRecord(
            project_id=project.id,
            user_id=user.id,
            format=fmt,
            storage_key=storage_key,
            filename=filename,
            file_size_bytes=len(file_bytes),
            download_count=1,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return record, file_bytes
