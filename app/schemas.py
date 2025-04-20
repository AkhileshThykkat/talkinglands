from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from shapely.geometry import Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
import json


# Base Point Schemas
class PointBase(BaseModel):
    name: str
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class PointCreate(PointBase):
    coordinates: List[float] = Field(..., min_items=2, max_items=2)

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class PointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    coordinates: Optional[List[float]] = Field(None, min_items=2, max_items=2)

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class PointInDB(PointBase):
    id: int
    created_at: datetime
    updated_at: datetime
    geometry: Dict[str, Any]

    class Config:
        from_attributes = True


class PointBatchCreate(BaseModel):
    points: List[PointCreate]


# Base Polygon Schemas
class PolygonBase(BaseModel):
    name: str
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class PolygonCreate(PolygonBase):
    coordinates: List[List[float]] = Field(..., min_items=3)

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 coordinates")

        # Check coordinate format and bounds
        for coord in v:
            if len(coord) != 2:
                raise ValueError("Each coordinate must be [longitude, latitude]")
            lon, lat = coord
            if not (-180 <= lon <= 180):
                raise ValueError(f"Longitude {lon} must be between -180 and 180")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} must be between -90 and 90")

        # Ensure first and last coordinates are the same for closed polygon
        if v[0] != v[-1]:
            v.append(v[0])

        return v


class PolygonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    coordinates: Optional[List[List[float]]] = None

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if v is None:
            return v

        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 coordinates")

        # Check coordinate format and bounds
        for coord in v:
            if len(coord) != 2:
                raise ValueError("Each coordinate must be [longitude, latitude]")
            lon, lat = coord
            if not (-180 <= lon <= 180):
                raise ValueError(f"Longitude {lon} must be between -180 and 180")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} must be between -90 and 90")

        # Ensure first and last coordinates are the same for closed polygon
        if v[0] != v[-1]:
            v.append(v[0])

        return v


class PolygonInDB(PolygonBase):
    id: int
    created_at: datetime
    updated_at: datetime
    geometry: Dict[str, Any]

    class Config:
        from_attributes = True


class PolygonBatchCreate(BaseModel):
    polygons: List[PolygonCreate]


# GeoJSON Feature Collections
class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
