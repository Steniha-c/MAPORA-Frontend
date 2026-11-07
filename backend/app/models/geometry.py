"""Spatial geometry models: FloorPlan, Room, Wall, DoorWindow, NavigationPath, Model3D."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project


class FloorPlan(Base, TimestampMixin):
    """2D Floor Plan entity containing rooms, walls, and openings."""

    __tablename__ = "floor_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    coordinate_system: Mapped[str] = mapped_column(
        String(50), default="normalized-cartesian-2d", nullable=False
    )
    units: Mapped[str] = mapped_column(String(20), default="meters", nullable=False)
    measurements_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="floor_plans")
    rooms: Mapped[List["Room"]] = relationship(
        "Room", back_populates="floor_plan", cascade="all, delete-orphan"
    )
    walls: Mapped[List["Wall"]] = relationship(
        "Wall", back_populates="floor_plan", cascade="all, delete-orphan"
    )
    openings: Mapped[List["DoorWindow"]] = relationship(
        "DoorWindow", back_populates="floor_plan", cascade="all, delete-orphan"
    )
    navigation_paths: Mapped[List["NavigationPath"]] = relationship(
        "NavigationPath", back_populates="floor_plan", cascade="all, delete-orphan"
    )


class Room(Base, TimestampMixin):
    """Room polygon and bounding box within a floor plan."""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    floor_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floor_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), default="Room", nullable=False)
    bounds_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounds_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounds_width: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    bounds_height: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    polygon_points: Mapped[Optional[List[Dict[str, float]]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)

    # Relationships
    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="rooms")


class Wall(Base, TimestampMixin):
    """Wall segment or door opening boundary."""

    __tablename__ = "walls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    floor_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floor_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    end_x: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    end_y: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="wall", nullable=False)  # 'wall' or 'door'
    thickness: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)

    # Relationships
    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="walls")


class DoorWindow(Base, TimestampMixin):
    """Door or window opening located along walls."""

    __tablename__ = "door_windows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    floor_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floor_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    wall_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    opening_type: Mapped[str] = mapped_column(String(20), default="door", nullable=False)  # 'door' | 'window'
    x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    width: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    orientation_deg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="openings")


class NavigationPath(Base, TimestampMixin):
    """Estimated walkthrough camera trajectory or inferred connectivity path."""

    __tablename__ = "navigation_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    floor_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floor_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    waypoints: Mapped[List[Dict[str, float]]] = mapped_column(JSON, default=list, nullable=False)
    length_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="navigation_paths")


class Model3D(Base, TimestampMixin):
    """Generated 3D mesh representation (GLB / glTF) with interactive room nodes."""

    __tablename__ = "models_3d"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    format: Mapped[str] = mapped_column(String(20), default="glb", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vertex_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    face_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="models3d")
