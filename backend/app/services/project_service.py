"""Project business logic service."""

from typing import List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.security import UserRole
from app.models.project import Project
from app.models.version import ProjectVersion
from app.models.geometry import FloorPlan, Room, Wall
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """Service handling project CRUD, permissions, and version histories."""

    @staticmethod
    def get_project_with_auth(db: Session, project_id: str, user: User) -> Optional[Project]:
        """Fetch project ensuring user has ownership or admin permissions."""
        project = db.scalar(select(Project).where(Project.id == project_id, Project.is_archived.is_(False)))
        if not project:
            return None
        if user.role != UserRole.ADMIN.value and project.user_id != user.id:
            return None
        return project

    @staticmethod
    def create_project(db: Session, user: User, project_in: ProjectCreate) -> Project:
        project = Project(
            name=project_in.name,
            location=project_in.location or "Indoor Survey Site",
            color=project_in.color or "blue",
            status="Needs attention",
            rooms_count=0,
            duration="00:00",
            version_count=1,
            user_id=user.id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create initial Version 1 snapshot
        initial_version = ProjectVersion(
            project_id=project.id,
            version_number=1,
            description="Initial project creation",
            status="active",
            created_by=user.id,
            floor_plan_snapshot=None,
        )
        db.add(initial_version)
        db.commit()

        return project

    @staticmethod
    def list_projects(
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Project]:
        query = select(Project).where(Project.is_archived.is_(False))

        # Enforce surveyor role isolation
        if user.role != UserRole.ADMIN.value:
            query = query.where(Project.user_id == user.id)

        if search:
            query = query.where(Project.name.ilike(f"%{search.strip()}%"))

        if status:
            query = query.where(Project.status == status)

        query = query.order_by(desc(Project.created_at)).offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
        if project_in.name is not None:
            project.name = project_in.name
        if project_in.location is not None:
            project.location = project_in.location
        if project_in.color is not None:
            project.color = project_in.color
        if project_in.status is not None:
            project.status = project_in.status

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project: Project) -> None:
        """Permanently delete project and cascade child relations."""
        db.delete(project)
        db.commit()

    @staticmethod
    def list_versions(db: Session, project: Project) -> List[ProjectVersion]:
        query = (
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project.id)
            .order_by(desc(ProjectVersion.version_number))
        )
        return list(db.scalars(query).all())

    @staticmethod
    def create_version_snapshot(
        db: Session,
        project: Project,
        user: User,
        description: Optional[str] = None,
    ) -> ProjectVersion:
        # Fetch current active floor plan
        active_plan = db.scalar(
            select(FloorPlan).where(FloorPlan.project_id == project.id, FloorPlan.is_active.is_(True))
        )

        snapshot_data = None
        if active_plan:
            snapshot_data = {
                "coordinateSystem": active_plan.coordinate_system,
                "units": active_plan.units,
                "rooms": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "bounds": {"x": r.bounds_x, "y": r.bounds_y, "width": r.bounds_width, "height": r.bounds_height},
                        "areaSquareMeters": r.area_sqm,
                    }
                    for r in active_plan.rooms
                ],
                "walls": [
                    {
                        "id": w.id,
                        "start": {"x": w.start_x, "y": w.start_y},
                        "end": {"x": w.end_x, "y": w.end_y},
                        "kind": w.kind,
                    }
                    for w in active_plan.walls
                ],
            }

        new_version_num = project.version_count + 1
        project.version_count = new_version_num

        version = ProjectVersion(
            project_id=project.id,
            version_number=new_version_num,
            description=description or f"Snapshot version {new_version_num}",
            status="active",
            created_by=user.id,
            floor_plan_snapshot=snapshot_data,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def restore_version(db: Session, project: Project, version_id: str, user: User) -> bool:
        version = db.scalar(
            select(ProjectVersion).where(
                ProjectVersion.id == version_id,
                ProjectVersion.project_id == project.id,
            )
        )
        if not version or not version.floor_plan_snapshot:
            return False

        snapshot = version.floor_plan_snapshot

        # Archive current active floor plan
        current_plan = db.scalar(
            select(FloorPlan).where(FloorPlan.project_id == project.id, FloorPlan.is_active.is_(True))
        )
        if current_plan:
            current_plan.is_active = False

        # Create new restored floor plan
        restored_plan = FloorPlan(
            project_id=project.id,
            coordinate_system=snapshot.get("coordinateSystem", "normalized-cartesian-2d"),
            units=snapshot.get("units", "meters"),
            measurements_available=True,
            quality_confidence=0.90,
            is_active=True,
        )
        db.add(restored_plan)
        db.flush()

        for r in snapshot.get("rooms", []):
            b = r.get("bounds", {})
            room = Room(
                floor_plan_id=restored_plan.id,
                name=r.get("name", "Room"),
                bounds_x=b.get("x", 0.0),
                bounds_y=b.get("y", 0.0),
                bounds_width=b.get("width", 1.0),
                bounds_height=b.get("height", 1.0),
                area_sqm=r.get("areaSquareMeters"),
            )
            db.add(room)

        for w in snapshot.get("walls", []):
            s = w.get("start", {})
            e = w.get("end", {})
            wall = Wall(
                floor_plan_id=restored_plan.id,
                start_x=s.get("x", 0.0),
                start_y=s.get("y", 0.0),
                end_x=e.get("x", 1.0),
                end_y=e.get("y", 1.0),
                kind=w.get("kind", "wall"),
            )
            db.add(wall)

        project.rooms_count = len(snapshot.get("rooms", []))
        project.status = "Ready"
        db.commit()
        return True
