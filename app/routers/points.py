from typing import List, Optional
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query

# from geoalchemy2 import Geography
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import cast, func, select
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_GeomFromText,
    ST_SetSRID,
    ST_MakePoint,
    ST_DWithin,
)

# from geoalchemy2.elements import WKTElement
import json

# from sqlalchemy import select, func
from geoalchemy2 import WKTElement
from geoalchemy2.types import Geography

# from fastapi import HTTPException
# import traceback

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/points", tags=["Points"])


@router.post("/", response_model=dict, status_code=201)
async def create_point(point: schemas.PointCreate, db: AsyncSession = Depends(get_db)):
    """Create a new spatial point"""
    try:
        lon, lat = point.coordinates  # Get the latitude and longitude from Body
        wkt_point = f"POINT({lon} {lat})"  # Pre-formatting for saving to database
        db_point = models.SpatialPoint(
            name=point.name,
            description=point.description,
            attributes=point.attributes,
            geom=WKTElement(
                wkt_point, srid=4326
            ),  # Converting string to GeoAlchemy Point Class for saving to database
        )

        db.add(db_point)
        await db.commit()
        await db.refresh(db_point)

        return db_point.to_geojson()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.post("/batch", response_model=schemas.FeatureCollection, status_code=201)
async def create_points_batch(
    points_data: schemas.PointBatchCreate, db: AsyncSession = Depends(get_db)
):
    """Create multiple spatial points in a batch"""
    try:
        features = []

        for point in points_data.points:
            lon, lat = point.coordinates
            wkt_point = f"POINT({lon} {lat})"

            db_point = models.SpatialPoint(
                name=point.name,
                description=point.description,
                attributes=point.attributes,
                geom=WKTElement(wkt_point, srid=4326),
            )

            db.add(db_point)
            await db.flush()
            features.append(db_point.to_geojson())

        await db.commit()

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.get("/", response_model=schemas.FeatureCollection)
async def get_all_points(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        """Get all spatial points with optional filtering by name"""
        query = select(models.SpatialPoint)

        if name:
            query = query.where(models.SpatialPoint.name.ilike(f"%{name}%"))

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        points = result.scalars().all()
        if not points:
            return {"type": "FeatureCollection", "features": []}
        features = [point.to_geojson() for point in points]
        return {"type": "FeatureCollection", "features": features}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.get("/{point_id}", response_model=dict)
async def get_point(point_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific spatial point by ID"""
    try:
        query = select(models.SpatialPoint).where(models.SpatialPoint.id == point_id)
        result = await db.execute(query)
        point = result.scalar_one_or_none()
        if not point:
            raise HTTPException(status_code=404, detail="Point not found")

        return point.to_geojson()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.put("/{point_id}", response_model=dict)
async def update_point(
    point_id: int, point_update: schemas.PointUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a spatial point"""
    query = select(models.SpatialPoint).where(models.SpatialPoint.id == point_id)
    result = await db.execute(query)
    db_point = result.scalar_one_or_none()

    if not db_point:
        raise HTTPException(status_code=404, detail="Point not found")

    # Update basic attributes
    if point_update.name is not None:
        db_point.name = point_update.name
    if point_update.description is not None:
        db_point.description = point_update.description
    if point_update.attributes is not None:
        db_point.attributes = point_update.attributes

    # Update geometry if coordinates provided
    if point_update.coordinates:
        lon, lat = point_update.coordinates
        wkt_point = f"POINT({lon} {lat})"
        db_point.geom = WKTElement(wkt_point, srid=4326)

    try:
        await db.commit()
        await db.refresh(db_point)
        return db_point.to_geojson()
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.delete("/{point_id}", status_code=204)
async def delete_point(point_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a spatial point"""
    try:
        query = select(models.SpatialPoint).where(models.SpatialPoint.id == point_id)
        result = await db.execute(query)
        db_point = result.scalar_one_or_none()

        if not db_point:
            raise HTTPException(status_code=404, detail="Point not found")

        try:
            await db.delete(db_point)
            await db.commit()
            return {"status": "success"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to delete point: {str(e)}"
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )
