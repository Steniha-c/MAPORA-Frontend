"""Pydantic schemas for 2D Floor Plan representation and updates."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Point2D(BaseModel):
    """2D point coordinate."""
    x: float
    y: float


class Bounds2D(BaseModel):
    """2D bounding rectangle."""
    x: float
    y: float
    width: float
    height: float


class FloorPlanRoom(BaseModel):
    """Room schema matching frontend FloorPlanRoom."""
    id: str
    name: str
    bounds: Bounds2D
    area_square_meters: Optional[float] = Field(default=None, alias="areaSquareMeters")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class FloorPlanWall(BaseModel):
    """Wall or door segment schema matching frontend FloorPlanWall."""
    id: str
    start: Point2D
    end: Point2D
    kind: str = "wall"  # 'wall' | 'door'

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class FloorPlanModel(BaseModel):
    """2D Floor Plan model strictly matching frontend FloorPlanModel."""
    coordinate_system: str = Field(default="normalized-cartesian-2d", alias="coordinateSystem")
    units: str = "meters"
    measurements_available: bool = Field(default=True, alias="measurementsAvailable")
    rooms: List[FloorPlanRoom] = Field(default_factory=list)
    walls: List[FloorPlanWall] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class RoomUpdateItem(BaseModel):
    """Update item for modifying room properties (e.g. name or bounds)."""
    id: str
    name: Optional[str] = None
    bounds: Optional[Bounds2D] = None
    area_square_meters: Optional[float] = Field(default=None, alias="areaSquareMeters")

    model_config = ConfigDict(populate_by_name=True)


class WallUpdateItem(BaseModel):
    """Update item for wall/door modifications."""
    id: str
    start: Optional[Point2D] = None
    end: Optional[Point2D] = None
    kind: Optional[str] = None


class FloorPlanUpdate(BaseModel):
    """Schema for updating floor plan geometry and room labels."""
    rooms: Optional[List[RoomUpdateItem]] = None
    walls: Optional[List[WallUpdateItem]] = None
    units: Optional[str] = None
