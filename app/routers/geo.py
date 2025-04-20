import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromText, ST_SetSRID
from geoalchemy2.elements import WKTElement
import json

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/geo", tags=["Polygons"])


@router.get("/intersect", response_model=schemas.FeatureCollection)
async def find_intersecting_polygons(
    coordinates: str = Query(..., description="JSON-encoded list of [lon, lat] pairs"),
    db: AsyncSession = Depends(get_db),
):
    """Find all polygons that intersect with the provided polygon"""
    try:
        coords = json.loads(coordinates)
        # Format coordinates as WKT polygon string
        coord_strings = [f"{lon} {lat}" for lon, lat in coords]
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
