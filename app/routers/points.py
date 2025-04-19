# app/api/endpoints/points.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_GeomFromText,
    ST_SetSRID,
    ST_MakePoint,
    ST_DWithin,
)
from geoalchemy2.elements import WKTElement
import json

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("/", response_model=dict, status_code=201)
def create_point(point: schemas.PointCreate, db: Session = Depends(get_db)):
    """Create a new spatial point"""
    try:
        lon, lat = point.coordinates
        wkt_point = f"POINT({lon} {lat})"

        # Create database record
        db_point = models.SpatialPoint(
            name=point.name,
            description=point.description,
            attributes=point.attributes,
            geom=WKTElement(wkt_point, srid=4326),
        )

        db.add(db_point)
        db.commit()
        db.refresh(db_point)

        return db_point.to_geojson()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create point: {str(e)}")


@router.post("/batch", response_model=schemas.FeatureCollection, status_code=201)
def create_points_batch(
    points_data: schemas.PointBatchCreate, db: Session = Depends(get_db)
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
            db.flush()  # Flush to get IDs without committing
            features.append(db_point.to_geojson())

        db.commit()

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create batch points: {str(e)}"
        )


@router.get("/", response_model=schemas.FeatureCollection)
def get_all_points(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all spatial points with optional filtering by name"""
    query = db.query(models.SpatialPoint)

    if name:
        query = query.filter(models.SpatialPoint.name.ilike(f"%{name}%"))

    points = query.offset(skip).limit(limit).all()
    features = [point.to_geojson() for point in points]

    return {"type": "FeatureCollection", "features": features}


@router.get("/{point_id}", response_model=dict)
def get_point(point_id: int, db: Session = Depends(get_db)):
    """Get a specific spatial point by ID"""
    point = (
        db.query(models.SpatialPoint).filter(models.SpatialPoint.id == point_id).first()
    )

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    return point.to_geojson()


@router.put("/{point_id}", response_model=dict)
def update_point(
    point_id: int, point_update: schemas.PointUpdate, db: Session = Depends(get_db)
):
    """Update a spatial point"""
    db_point = (
        db.query(models.SpatialPoint).filter(models.SpatialPoint.id == point_id).first()
    )

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
        db.commit()
        db.refresh(db_point)
        return db_point.to_geojson()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update point: {str(e)}")


@router.delete("/{point_id}", status_code=204)
def delete_point(point_id: int, db: Session = Depends(get_db)):
    """Delete a spatial point"""
    db_point = (
        db.query(models.SpatialPoint).filter(models.SpatialPoint.id == point_id).first()
    )

    if not db_point:
        raise HTTPException(status_code=404, detail="Point not found")

    try:
        db.delete(db_point)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete point: {str(e)}")


@router.get("/search/radius", response_model=schemas.FeatureCollection)
def search_points_by_radius(
    lon: float = Query(..., description="Longitude of the center point"),
    lat: float = Query(..., description="Latitude of the center point"),
    radius: float = Query(..., description="Search radius in meters"),
    db: Session = Depends(get_db),
):
    """Search for points within a specified radius of a location"""
    try:
        # Using geography type for accurate distance calculation
        point_wkt = f"POINT({lon} {lat})"
        center_point = WKTElement(point_wkt, srid=4326)

        points = (
            db.query(models.SpatialPoint)
            .filter(
                func.ST_DWithin(
                    models.SpatialPoint.geom.cast("geography"),
                    center_point.cast("geography"),
                    radius,
                )
            )
            .all()
        )

        features = []
        for point in points:
            feature = point.to_geojson()
            # Calculate distance from center point
            distance = db.scalar(
                func.ST_Distance(
                    models.SpatialPoint.geom.cast("geography"),
                    center_point.cast("geography"),
                ).label("distance")
            )
            feature["properties"]["distance"] = (
                float(distance) if distance is not None else None
            )
            features.append(feature)

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search points by radius: {str(e)}"
        )
