import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromText, ST_SetSRID
from geoalchemy2.elements import WKTElement
import json

from app.database import get_db
from app import models, schemas

router = APIRouter("/api/polygons")


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
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
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
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to create point: {str(e)}",
                "error_root": traceback.format_exc(),  ## Used only for debugging  can remove in production
            },
        )


@router.get("/", response_model=schemas.FeatureCollection)
async def get_all_polygons(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        query = select(models.SpatialPolygon)

        if name:
            query = query.where(models.SpatialPolygon.name.ilike(f"%{name}%"))

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        polygons = result.scalars().all()

        features = [polygon.to_geojson() for polygon in polygons]

        return {"type": "FeatureCollection", "features": features}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to fetch polygons: {str(e)}",
                "error_root": traceback.format_exc(),  # Remove in production
            },
        )


@router.get("/{polygon_id}", response_model=dict)
async def get_polygon(polygon_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific spatial polygon by ID"""
    try:
        query = select(models.SpatialPolygon).where(
            models.SpatialPolygon.id == polygon_id
        )

        result = await db.execute(query)
        polygon = result.scalars().first()

        if not polygon:
            raise HTTPException(status_code=404, detail="Polygon not found")

        return polygon.to_geojson()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to fetch polygons: {str(e)}",
                "error_root": traceback.format_exc(),  # Remove in production
            },
        )


@router.put("/{polygon_id}", response_model=dict)
async def update_polygon(
    polygon_id: int,
    polygon_update: schemas.PolygonUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        """Update a spatial polygon"""
        query = select(models.SpatialPolygon).where(
            models.SpatialPolygon.id == polygon_id
        )

        result = await db.execute(query)
        db_polygon = result.scalars().first()

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

        await db.commit()
        await db.refresh(db_polygon)
        return db_polygon.to_geojson()
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


@router.delete("/{polygon_id}", status_code=204)
async def delete_polygon(polygon_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a spatial polygon"""
    try:
        query = select(models.SpatialPolygon).where(
            models.SpatialPolygon.id == polygon_id
        )

        result = await db.execute(query)
        db_polygon = result.scalars().first()

        if not db_polygon:
            raise HTTPException(status_code=404, detail="Polygon not found")

        await db.delete(db_polygon)
        await db.commit()
        return {"status": "success"}
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete polygon: {str(e)}"
        )


@router.get("/{polygon_id}/points", response_model=schemas.FeatureCollection)
async def find_points_within_polygon(
    polygon_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Find all points that fall within a specific polygon"""
    try:
        # Fetch polygon by ID
        polygon_query = select(models.SpatialPolygon).where(
            models.SpatialPolygon.id == polygon_id
        )
        polygon_result = await db.execute(polygon_query)
        polygon = polygon_result.scalars().first()

        if not polygon:
            raise HTTPException(status_code=404, detail="Polygon not found")

        # Query points within polygon geometry
        points_query = select(models.SpatialPoint).where(
            func.ST_Within(models.SpatialPoint.geom, polygon.geom)
        )
        points_result = await db.execute(points_query)
        points = points_result.scalars().all()

        features = [point.to_geojson() for point in points]

        return {"type": "FeatureCollection", "features": features}

    except HTTPException as e:
        raise e
    except Exception as e:
        # await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to find points within polygon: {str(e)}",
                "error_root": traceback.format_exc(),  # Remove in production
            },
        )


@router.get("/intersect", response_model=schemas.FeatureCollection)
async def find_intersecting_polygons(
    coordinates: List[List[float]] = Query(
        ..., description="List of coordinate pairs defining a polygon"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Find all polygons that intersect with the provided polygon"""
    try:
        # Format coordinates as WKT polygon string
        coord_strings = [f"{lon} {lat}" for lon, lat in coordinates]
        if coord_strings[0] != coord_strings[-1]:
            coord_strings.append(coord_strings[0])  # Close polygon ring

        wkt_polygon = f'POLYGON(({", ".join(coord_strings)}))'
        query_geom = WKTElement(wkt_polygon, srid=4326)

        polygons_query = select(models.SpatialPolygon).where(
            func.ST_Intersects(models.SpatialPolygon.geom, query_geom)
        )
        polygons_result = await db.execute(polygons_query)
        polygons = polygons_result.scalars().all()

        features = [polygon.to_geojson() for polygon in polygons]

        return {"type": "FeatureCollection", "features": features}

    except HTTPException as e:
        raise e
    except Exception as e:
        # await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to find intersecting polygons: {str(e)}",
                "error_root": traceback.format_exc(),
            },
        )


@router.get("/contains", response_model=schemas.FeatureCollection)
async def find_polygons_containing_point(
    lon: float = Query(..., description="Longitude of the point"),
    lat: float = Query(..., description="Latitude of the point"),
    db: AsyncSession = Depends(get_db),
):
    """Find all polygons that contain the specified point"""
    try:
        point_wkt = f"POINT({lon} {lat})"
        point_geom = WKTElement(point_wkt, srid=4326)

        polygons_query = select(models.SpatialPolygon).where(
            func.ST_Contains(models.SpatialPolygon.geom, point_geom)
        )
        polygons_result = await db.execute(polygons_query)
        polygons = polygons_result.scalars().all()

        features = [polygon.to_geojson() for polygon in polygons]

        return {"type": "FeatureCollection", "features": features}

    except HTTPException as e:
        raise e
    except Exception as e:
        # await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "msg": f"Failed to find polygons containing point: {str(e)}",
                "error_root": traceback.format_exc(),
            },
        )
