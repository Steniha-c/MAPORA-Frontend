"""Floor plan querying and interactive editing service."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geometry import FloorPlan, Room, Wall
from app.models.project import Project
from app.models.user import User
from app.schemas.floor_plan import FloorPlanModel, FloorPlanRoom, FloorPlanWall, Bounds2D, Point2D, FloorPlanUpdate
from app.services.project_service import ProjectService
from app.services.audit_service import AuditService


class FloorPlanService:
    """Service providing floor plan retrieval, interactive edits, and version creation."""

    @staticmethod
    def get_active_floor_plan(db: Session, project: Project) -> Optional[FloorPlanModel]:
        plan = db.scalar(
            select(FloorPlan).where(
                FloorPlan.project_id == project.id,
                FloorPlan.is_active.is_(True),
            )
        )
        if not plan:
            return None

        rooms = [
            FloorPlanRoom(
                id=r.id,
                name=r.name,
                bounds=Bounds2D(x=r.bounds_x, y=r.bounds_y, width=r.bounds_width, height=r.bounds_height),
                areaSquareMeters=r.area_sqm,
            )
            for r in plan.rooms
        ]

        walls = [
            FloorPlanWall(
                id=w.id,
                start=Point2D(x=w.start_x, y=w.start_y),
                end=Point2D(x=w.end_x, y=w.end_y),
                kind=w.kind,
            )
            for w in plan.walls
        ]

        return FloorPlanModel(
            coordinateSystem=plan.coordinate_system,
            units=plan.units,
            measurementsAvailable=plan.measurements_available,
            rooms=rooms,
            walls=walls,
        )

    @staticmethod
    def update_floor_plan(
        db: Session,
        project: Project,
        user: User,
        update_in: FloorPlanUpdate,
    ) -> FloorPlanModel:
        plan = db.scalar(
            select(FloorPlan).where(
                FloorPlan.project_id == project.id,
                FloorPlan.is_active.is_(True),
            )
        )
        if not plan:
            raise ValueError("No active floor plan found for this project.")

        # Update room attributes
        if update_in.rooms:
            for item in update_in.rooms:
                room = db.scalar(select(Room).where(Room.id == item.id, Room.floor_plan_id == plan.id))
                if room:
                    if item.name is not None:
                        room.name = item.name.strip()
                    if item.bounds is not None:
                        if item.bounds.width <= 0 or item.bounds.height <= 0:
                            raise ValueError(f"Invalid room bounds: width and height must be positive.")
                        room.bounds_x = item.bounds.x
                        room.bounds_y = item.bounds.y
                        room.bounds_width = item.bounds.width
                        room.bounds_height = item.bounds.height
                        room.area_sqm = round(item.bounds.width * item.bounds.height, 2)
                    elif item.area_square_meters is not None:
                        room.area_sqm = item.area_square_meters

        # Update wall attributes
        if update_in.walls:
            for item in update_in.walls:
                wall = db.scalar(select(Wall).where(Wall.id == item.id, Wall.floor_plan_id == plan.id))
                if wall:
                    if item.start is not None:
                        wall.start_x = item.start.x
                        wall.start_y = item.start.y
                    if item.end is not None:
                        wall.end_x = item.end.x
                        wall.end_y = item.end.y
                    if item.kind is not None:
                        if item.kind not in ["wall", "door", "window"]:
                            raise ValueError(f"Invalid wall kind: {item.kind}")
                        wall.kind = item.kind

        if update_in.units:
            plan.units = update_in.units

        db.commit()

        # Create version snapshot and audit log to preserve history
        ProjectService.create_version_snapshot(
            db, project, user, description=f"Edited floor plan by {user.email}"
        )
        AuditService.log(
            db,
            action="edit_floor_plan",
            user_id=user.id,
            project_id=project.id,
            details=f"Updated floor plan geometry and labels.",
        )

        return FloorPlanService.get_active_floor_plan(db, project)
