# app/models.py
from typing import Any
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

# import json


class Base(DeclarativeBase, AsyncAttrs):
    pass


class SpatialPoint(Base):
    __tablename__ = "spatial_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Create spatial index
    __table_args__ = (Index("idx_spatial_points_geom", geom, postgresql_using="gist"),)

    def to_geojson(self):
        """Convert to GeoJSON feature format"""
        point_shape = to_shape(self.geom)
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": mapping(point_shape),
            "properties": {
                "name": self.name,
                "description": self.description,
                "attributes": self.attributes,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            },
        }


class SpatialPolygon(Base):
    __tablename__ = "spatial_polygons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Create spatial index
    __table_args__ = (
        Index("idx_spatial_polygons_geom", geom, postgresql_using="gist"),
    )

    def to_geojson(self):
        """Convert to GeoJSON feature format"""
        polygon_shape = to_shape(self.geom)
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": mapping(polygon_shape),
            "properties": {
                "name": self.name,
                "description": self.description,
                "attributes": self.attributes,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            },
        }
