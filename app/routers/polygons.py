from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromText, ST_SetSRID
from geoalchemy2.elements import WKTElement
import json

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("/", response_model=dict, status_code=201)
async def create_polygon(
    polygon: schemas.PolygonCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new spatial polygon"""
    try:
        # Format coordinates as WKT
        coord_strings = [f"{lon} {lat}" for lon, lat in polygon.coordinates]
        wkt_polygon = f'POLYGON(({", ".join(coord_strings)}))'

        # Create database record
        db_polygon = models.SpatialPolygon(
            name=polygon.name,
            description=polygon.description,
            attributes=polygon.attributes,
            geom=WKTElement(wkt_polygon, srid=4326),
        )

        db.add(db_polygon)
        await db.commit()
        await db.refresh(db_polygon)

        return db_polygon.to_geojson()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create polygon: {str(e)}"
        )


@router.post("/batch", response_model=schemas.FeatureCollection, status_code=201)
async def create_polygons_batch(
    polygons_data: schemas.PolygonBatchCreate, db: AsyncSession = Depends(get_db)
):
    """Create multiple spatial polygons in a batch"""
    try:
        features = []

        for polygon in polygons_data.polygons:
            # Format coordinates as WKT
            coord_strings = [f"{lon} {lat}" for lon, lat in polygon.coordinates]
            wkt_polygon = f'POLYGON(({", ".join(coord_strings)}))'

            db_polygon = models.SpatialPolygon(
                name=polygon.name,
                description=polygon.description,
                attributes=polygon.attributes,
                geom=WKTElement(wkt_polygon, srid=4326),
            )

            db.add(db_polygon)
            await db.flush()  # Flush to get IDs without committing
            features.append(db_polygon.to_geojson())

        await db.commit()

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create batch polygons: {str(e)}"
        )


@router.get("/", response_model=schemas.FeatureCollection)
async def get_all_polygons(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all spatial polygons with optional filtering by name"""
    query = db.query(models.SpatialPolygon)

    if name:
        query = query.filter(models.SpatialPolygon.name.ilike(f"%{name}%"))

    polygons = query.offset(skip).limit(limit).all()
    features = [polygon.to_geojson() for polygon in polygons]

    return {"type": "FeatureCollection", "features": features}


@router.get("/{polygon_id}", response_model=dict)
def get_polygon(polygon_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific spatial polygon by ID"""
    polygon = (
        db.query(models.SpatialPolygon)
        .filter(models.SpatialPolygon.id == polygon_id)
        .first()
    )

    if not polygon:
        raise HTTPException(status_code=404, detail="Polygon not found")

    return polygon.to_geojson()


@router.put("/{polygon_id}", response_model=dict)
def update_polygon(
    polygon_id: int,
    polygon_update: schemas.PolygonUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a spatial polygon"""
    db_polygon = (
        db.query(models.SpatialPolygon)
        .filter(models.SpatialPolygon.id == polygon_id)
        .first()
    )

    if not db_polygon:
        raise HTTPException(status_code=404, detail="Polygon not found")

    # Update basic attributes
    if polygon_update.name is not None:
        db_polygon.name = polygon_update.name
    if polygon_update.description is not None:
        db_polygon.description = polygon_update.description
    if polygon_update.attributes is not None:
        db_polygon.attributes = polygon_update.attributes

    # Update geometry if coordinates provided
    if polygon_update.coordinates:
        coord_strings = [f"{lon} {lat}" for lon, lat in polygon_update.coordinates]
        wkt_polygon = f'POLYGON(({", ".join(coord_strings)}))'
        db_polygon.geom = WKTElement(wkt_polygon, srid=4326)

    try:
        db.commit()
        db.refresh(db_polygon)
        return db_polygon.to_geojson()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update polygon: {str(e)}"
        )


@router.delete("/{polygon_id}", status_code=204)
def delete_polygon(polygon_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a spatial polygon"""
    db_polygon = (
        db.query(models.SpatialPolygon)
        .filter(models.SpatialPolygon.id == polygon_id)
        .first()
    )

    if not db_polygon:
        raise HTTPException(status_code=404, detail="Polygon not found")

    try:
        db.delete(db_polygon)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete polygon: {str(e)}"
        )


@router.get("/{polygon_id}/points", response_model=schemas.FeatureCollection)
def find_points_within_polygon(polygon_id: int, db: AsyncSession = Depends(get_db)):
    """Find all points that fall within a specific polygon"""
    polygon = (
        db.query(models.SpatialPolygon)
        .filter(models.SpatialPolygon.id == polygon_id)
        .first()
    )

    if not polygon:
        raise HTTPException(status_code=404, detail="Polygon not found")

    try:
        points = (
            db.query(models.SpatialPoint)
            .filter(func.ST_Within(models.SpatialPoint.geom, polygon.geom))
            .all()
        )

        features = [point.to_geojson() for point in points]

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to find points within polygon: {str(e)}"
        )


@router.get("/intersect", response_model=schemas.FeatureCollection)
def find_intersecting_polygons(
    coordinates: List[List[float]] = Query(
        ..., description="List of coordinate pairs defining a polygon"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Find all polygons that intersect with the provided polygon"""
    try:
        # Format coordinates as WKT
        coord_strings = [f"{lon} {lat}" for lon, lat in coordinates]
        if coord_strings[0] != coord_strings[-1]:
            # Close the polygon
            coord_strings.append(coord_strings[0])

        wkt_polygon = f'POLYGON(({", ".join(coord_strings)}))'
        query_geom = WKTElement(wkt_polygon, srid=4326)

        polygons = (
            db.query(models.SpatialPolygon)
            .filter(func.ST_Intersects(models.SpatialPolygon.geom, query_geom))
            .all()
        )

        features = [polygon.to_geojson() for polygon in polygons]

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to find intersecting polygons: {str(e)}"
        )


@router.get("/contains", response_model=schemas.FeatureCollection)
def find_polygons_containing_point(
    lon: float = Query(..., description="Longitude of the point"),
    lat: float = Query(..., description="Latitude of the point"),
    db: AsyncSession = Depends(get_db),
):
    """Find all polygons that contain the specified point"""
    try:
        point_wkt = f"POINT({lon} {lat})"
        point_geom = WKTElement(point_wkt, srid=4326)

        polygons = (
            db.query(models.SpatialPolygon)
            .filter(func.ST_Contains(models.SpatialPolygon.geom, point_geom))
            .all()
        )

        features = [polygon.to_geojson() for polygon in polygons]

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find polygons containing point: {str(e)}",
        )
