import pytest
import httpx
import json
import asyncio
from typing import Dict, List, Tuple, Any

BASE_URL = "http://localhost:8080/api"  # Replace with your actual base URL

# ===== Helper Functions =====


async def create_test_point(
    coordinates: List[float],
    name: str = "Test Point",
    description: str = "A test point",
) -> int:
    """Create a test point and return its ID"""
    async with httpx.AsyncClient() as client:
        point_data = {
            "name": name,
            "description": description,
            "coordinates": coordinates,
            "attributes": {"test": "value"},
        }
        response = await client.post(f"{BASE_URL}/points/", json=point_data)
        assert response.status_code == 201
        return response.json()["id"]


async def create_test_polygon(
    coordinates: List[List[float]],
    name: str = "Test Polygon",
    description: str = "A test polygon",
) -> int:
    """Create a test polygon and return its ID"""
    async with httpx.AsyncClient() as client:
        polygon_data = {
            "name": name,
            "description": description,
            "coordinates": coordinates,
            "attributes": {"test": "value"},
        }
        response = await client.post(f"{BASE_URL}/polygons/", json=polygon_data)
        assert response.status_code == 201
        return response.json()["id"]


async def cleanup_point(point_id: int) -> None:
    """Delete a test point"""
    async with httpx.AsyncClient() as client:
        await client.delete(f"{BASE_URL}/points/{point_id}")


async def cleanup_polygon(polygon_id: int) -> None:
    """Delete a test polygon"""
    async with httpx.AsyncClient() as client:
        await client.delete(f"{BASE_URL}/polygons/{polygon_id}")


# ===== Point API Tests =====


@pytest.mark.asyncio
async def test_create_point():
    """Test creation of a single point"""
    async with httpx.AsyncClient() as client:
        point_data = {
            "name": "Test Point",
            "description": "A test point",
            "coordinates": [10.0, 20.0],
            "attributes": {"test": "value"},
        }
        response = await client.post(f"{BASE_URL}/points/", json=point_data)
        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json"
        point = response.json()
        assert point["type"] == "Feature"
        assert point["geometry"]["type"] == "Point"
        assert point["geometry"]["coordinates"] == [10.0, 20.0]
        assert point["properties"]["name"] == "Test Point"
        assert point["properties"]["description"] == "A test point"
        assert point["properties"]["attributes"]["test"] == "value"

        # Clean up
        await cleanup_point(point["id"])


@pytest.mark.asyncio
async def test_create_points_batch():
    """Test batch creation of points"""
    async with httpx.AsyncClient() as client:
        batch_data = {
            "points": [
                {
                    "name": "Batch Point 1",
                    "description": "First batch point",
                    "coordinates": [11.0, 21.0],
                    "attributes": {"batch": "1"},
                },
                {
                    "name": "Batch Point 2",
                    "description": "Second batch point",
                    "coordinates": [12.0, 22.0],
                    "attributes": {"batch": "2"},
                },
            ]
        }
        response = await client.post(f"{BASE_URL}/points/batch", json=batch_data)
        assert response.status_code == 201
        result = response.json()
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

        # Verify each point
        for i, feature in enumerate(result["features"]):
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Point"
            assert feature["properties"]["name"] == f"Batch Point {i+1}"

        # Clean up
        for feature in result["features"]:
            await cleanup_point(feature["id"])


@pytest.mark.asyncio
async def test_get_all_points():
    """Test retrieving all points with optional filtering"""
    # Create test points
    point_ids = []
    point_ids.append(await create_test_point([1.0, 1.0], name="Test Point Alpha"))
    point_ids.append(await create_test_point([2.0, 2.0], name="Test Point Beta"))
    point_ids.append(await create_test_point([3.0, 3.0], name="Another Point"))

    try:
        async with httpx.AsyncClient() as client:
            # Test getting all points
            response = await client.get(f"{BASE_URL}/points/")
            assert response.status_code == 200
            result = response.json()
            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) >= 3  # At least our 3 test points

            # Test filtering by name
            response = await client.get(f"{BASE_URL}/points/?name=Test Point")
            assert response.status_code == 200
            result = response.json()
            assert all(
                "Test Point" in feature["properties"]["name"]
                for feature in result["features"]
            )

            # Test pagination
            response = await client.get(f"{BASE_URL}/points/?limit=1")
            assert response.status_code == 200
            result = response.json()
            assert len(result["features"]) == 1

    finally:
        # Clean up
        for point_id in point_ids:
            await cleanup_point(point_id)


@pytest.mark.asyncio
async def test_get_point():
    """Test retrieving a specific point by ID"""
    point_id = await create_test_point([5.0, 5.0])

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/points/{point_id}")
            assert response.status_code == 200
            point = response.json()
            assert point["type"] == "Feature"
            assert point["id"] == point_id
            assert point["geometry"]["coordinates"] == [5.0, 5.0]

            # Test non-existent point
            response = await client.get(f"{BASE_URL}/points/99999")
            assert response.status_code == 404

    finally:
        await cleanup_point(point_id)


@pytest.mark.asyncio
async def test_update_point():
    """Test updating a point"""
    point_id = await create_test_point([5.0, 5.0])

    try:
        async with httpx.AsyncClient() as client:
            update_data = {
                "name": "Updated Point",
                "description": "An updated test point",
                "coordinates": [6.0, 6.0],
                "attributes": {"test": "updated value"},
            }
            response = await client.put(
                f"{BASE_URL}/points/{point_id}", json=update_data
            )
            assert response.status_code == 200
            updated_point = response.json()
            assert updated_point["properties"]["name"] == "Updated Point"
            assert updated_point["properties"]["description"] == "An updated test point"
            assert updated_point["geometry"]["coordinates"] == [6.0, 6.0]
            assert updated_point["properties"]["attributes"]["test"] == "updated value"

            # Verify with a GET request
            response = await client.get(f"{BASE_URL}/points/{point_id}")
            assert response.status_code == 200
            point = response.json()
            assert point["properties"]["name"] == "Updated Point"

    finally:
        await cleanup_point(point_id)


@pytest.mark.asyncio
async def test_delete_point():
    """Test deleting a point"""
    point_id = await create_test_point([5.0, 5.0])

    async with httpx.AsyncClient() as client:
        # Delete the point
        response = await client.delete(f"{BASE_URL}/points/{point_id}")
        assert response.status_code == 204

        # Verify deletion
        response = await client.get(f"{BASE_URL}/points/{point_id}")
        assert response.status_code == 404


# ===== Polygon API Tests =====


@pytest.mark.asyncio
async def test_create_polygon():
    """Test creating a polygon"""
    async with httpx.AsyncClient() as client:
        polygon_data = {
            "name": "Test Polygon",
            "description": "A test polygon",
            "coordinates": [
                [0.0, 0.0],
                [0.0, 10.0],
                [10.0, 10.0],
                [10.0, 0.0],
                [0.0, 0.0],
            ],
            "attributes": {"test": "value"},
        }
        response = await client.post(f"{BASE_URL}/polygons/", json=polygon_data)
        assert response.status_code == 201
        polygon = response.json()
        assert polygon["type"] == "Feature"
        assert polygon["geometry"]["type"] == "Polygon"
        assert polygon["properties"]["name"] == "Test Polygon"
        assert polygon["properties"]["description"] == "A test polygon"

        # Clean up
        await cleanup_polygon(polygon["id"])


@pytest.mark.asyncio
async def test_create_polygons_batch():
    """Test batch creation of polygons"""
    async with httpx.AsyncClient() as client:
        batch_data = {
            "polygons": [
                {
                    "name": "Batch Polygon 1",
                    "description": "First batch polygon",
                    "coordinates": [
                        [0.0, 0.0],
                        [0.0, 5.0],
                        [5.0, 5.0],
                        [5.0, 0.0],
                        [0.0, 0.0],
                    ],
                    "attributes": {"batch": "1"},
                },
                {
                    "name": "Batch Polygon 2",
                    "description": "Second batch polygon",
                    "coordinates": [
                        [10.0, 10.0],
                        [10.0, 15.0],
                        [15.0, 15.0],
                        [15.0, 10.0],
                        [10.0, 10.0],
                    ],
                    "attributes": {"batch": "2"},
                },
            ]
        }
        response = await client.post(f"{BASE_URL}/polygons/batch", json=batch_data)
        assert response.status_code == 201
        result = response.json()
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

        # Verify each polygon
        for i, feature in enumerate(result["features"]):
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Polygon"
            assert feature["properties"]["name"] == f"Batch Polygon {i+1}"

        # Clean up
        for feature in result["features"]:
            await cleanup_polygon(feature["id"])


@pytest.mark.asyncio
async def test_get_all_polygons():
    """Test retrieving all polygons with optional filtering"""
    # Create test polygons
    polygon_ids = []
    polygon_coords = [[0.0, 0.0], [0.0, 5.0], [5.0, 5.0], [5.0, 0.0], [0.0, 0.0]]

    polygon_ids.append(
        await create_test_polygon(polygon_coords, name="Test Polygon Alpha")
    )
    polygon_ids.append(
        await create_test_polygon(polygon_coords, name="Test Polygon Beta")
    )
    polygon_ids.append(
        await create_test_polygon(polygon_coords, name="Another Polygon")
    )

    try:
        async with httpx.AsyncClient() as client:
            # Test getting all polygons
            response = await client.get(f"{BASE_URL}/polygons/")
            assert response.status_code == 200
            result = response.json()
            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) >= 3  # At least our 3 test polygons

            # Test filtering by name
            response = await client.get(f"{BASE_URL}/polygons/?name=Test Polygon")
            assert response.status_code == 200
            result = response.json()
            assert all(
                "Test Polygon" in feature["properties"]["name"]
                for feature in result["features"]
            )

            # Test pagination
            response = await client.get(f"{BASE_URL}/polygons/?limit=1")
            assert response.status_code == 200
            result = response.json()
            assert len(result["features"]) == 1

    finally:
        # Clean up
        for polygon_id in polygon_ids:
            await cleanup_polygon(polygon_id)


@pytest.mark.asyncio
async def test_get_polygon():
    """Test retrieving a specific polygon by ID"""
    polygon_coords = [[0.0, 0.0], [0.0, 5.0], [5.0, 5.0], [5.0, 0.0], [0.0, 0.0]]
    polygon_id = await create_test_polygon(polygon_coords)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/polygons/{polygon_id}")
            assert response.status_code == 200
            polygon = response.json()
            assert polygon["type"] == "Feature"
            assert polygon["id"] == polygon_id
            assert polygon["geometry"]["type"] == "Polygon"
            assert polygon["properties"]["name"] == "Test Polygon"

            # Test non-existent polygon
            response = await client.get(f"{BASE_URL}/polygons/99999")
            assert response.status_code == 404

    finally:
        await cleanup_polygon(polygon_id)


@pytest.mark.asyncio
async def test_update_polygon():
    """Test updating a polygon"""
    original_coords = [[0.0, 0.0], [0.0, 5.0], [5.0, 5.0], [5.0, 0.0], [0.0, 0.0]]
    polygon_id = await create_test_polygon(original_coords)

    try:
        async with httpx.AsyncClient() as client:
            update_data = {
                "name": "Updated Polygon",
                "description": "An updated test polygon",
                "coordinates": [
                    [0.0, 0.0],
                    [0.0, 10.0],
                    [10.0, 10.0],
                    [10.0, 0.0],
                    [0.0, 0.0],
                ],
                "attributes": {"test": "updated value"},
            }
            response = await client.put(
                f"{BASE_URL}/polygons/{polygon_id}", json=update_data
            )
            assert response.status_code == 200
            updated_polygon = response.json()
            assert updated_polygon["properties"]["name"] == "Updated Polygon"
            assert (
                updated_polygon["properties"]["description"]
                == "An updated test polygon"
            )
            assert (
                updated_polygon["properties"]["attributes"]["test"] == "updated value"
            )

            # Verify with a GET request
            response = await client.get(f"{BASE_URL}/polygons/{polygon_id}")
            assert response.status_code == 200
            polygon = response.json()
            assert polygon["properties"]["name"] == "Updated Polygon"

    finally:
        await cleanup_polygon(polygon_id)


@pytest.mark.asyncio
async def test_delete_polygon():
    """Test deleting a polygon"""
    polygon_coords = [[0.0, 0.0], [0.0, 5.0], [5.0, 5.0], [5.0, 0.0], [0.0, 0.0]]
    polygon_id = await create_test_polygon(polygon_coords)

    async with httpx.AsyncClient() as client:
        # Delete the polygon
        response = await client.delete(f"{BASE_URL}/polygons/{polygon_id}")
        assert response.status_code == 204

        # Verify deletion
        response = await client.get(f"{BASE_URL}/polygons/{polygon_id}")
        assert response.status_code == 404


# ===== Spatial Query Tests =====


@pytest.mark.asyncio
async def test_find_points_within_polygon():
    """Test finding points within a polygon"""
    # Create a test polygon (simple square)
    polygon_coords = [[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0], [0.0, 0.0]]
    polygon_id = await create_test_polygon(polygon_coords)

    # Create points: inside and outside
    point_inside_id = await create_test_point([5.0, 5.0], name="Inside Point")
    point_edge_id = await create_test_point([0.0, 5.0], name="Edge Point")  # On edge
    point_outside_id = await create_test_point([15.0, 15.0], name="Outside Point")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/polygons/{polygon_id}/points")
            assert response.status_code == 200
            result = response.json()

            # Verify structure
            assert result["type"] == "FeatureCollection"
            assert isinstance(result["features"], list)

            # Check points found
            point_ids_found = [feature["id"] for feature in result["features"]]
            assert point_inside_id in point_ids_found
            # Edge behavior might vary by database/implementation
            assert point_outside_id not in point_ids_found

            # Test with invalid polygon ID
            response = await client.get(f"{BASE_URL}/polygons/99999/points")
            assert response.status_code == 404

    finally:
        # Clean up
        await cleanup_point(point_inside_id)
        await cleanup_point(point_edge_id)
        await cleanup_point(point_outside_id)
        await cleanup_polygon(polygon_id)


@pytest.mark.asyncio
async def test_find_intersecting_polygons():
    """Test finding polygons that intersect with a given polygon"""
    # Create test polygons
    polygon1_coords = [
        [0.0, 0.0],
        [0.0, 10.0],
        [10.0, 10.0],
        [10.0, 0.0],
        [0.0, 0.0],
    ]  # 0,0 to 10,10
    polygon2_coords = [
        [5.0, 5.0],
        [5.0, 15.0],
        [15.0, 15.0],
        [15.0, 5.0],
        [5.0, 5.0],
    ]  # 5,5 to 15,15 (intersects)
    polygon3_coords = [
        [20.0, 20.0],
        [20.0, 30.0],
        [30.0, 30.0],
        [30.0, 20.0],
        [20.0, 20.0],
    ]  # non-intersecting

    polygon1_id = await create_test_polygon(polygon1_coords, name="Polygon 1")
    polygon2_id = await create_test_polygon(polygon2_coords, name="Polygon 2")
    polygon3_id = await create_test_polygon(polygon3_coords, name="Polygon 3")

    try:
        async with httpx.AsyncClient() as client:
            # Test polygon that intersects with polygon1 and polygon2
            query_coords = [
                [7.0, 7.0],
                [7.0, 12.0],
                [12.0, 12.0],
                [12.0, 7.0],
                [7.0, 7.0],
            ]
            encoded_coords = json.dumps(query_coords)

            response = await client.get(
                f"{BASE_URL}/geo/intersect?coordinates={encoded_coords}"
            )
            assert response.status_code == 200
            result = response.json()

            # Verify structure
            assert result["type"] == "FeatureCollection"
            assert isinstance(result["features"], list)

            # Check correct polygons found
            polygon_ids_found = [feature["id"] for feature in result["features"]]
            assert polygon1_id in polygon_ids_found
            assert polygon2_id in polygon_ids_found
            assert polygon3_id not in polygon_ids_found

            # Test with malformed coordinates
            response = await client.get(f"{BASE_URL}/geo/intersect?coordinates=invalid")
            assert response.status_code == 500  # Expected for invalid JSON

    finally:
        # Clean up
        await cleanup_polygon(polygon1_id)
        await cleanup_polygon(polygon2_id)
        await cleanup_polygon(polygon3_id)


# ===== Error Handling Tests =====


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test error handling across various API endpoints"""
    async with httpx.AsyncClient() as client:
        # Invalid point data
        response = await client.post(f"{BASE_URL}/points/", json={"invalid": "data"})
        assert response.status_code in (400, 422)

        # Invalid polygon data
        response = await client.post(f"{BASE_URL}/polygons/", json={"invalid": "data"})
        assert response.status_code in (400, 422)

        # Invalid/non-existent IDs
        response = await client.get(f"{BASE_URL}/points/99999")
        assert response.status_code == 404

        response = await client.get(f"{BASE_URL}/polygons/99999")
        assert response.status_code == 404
