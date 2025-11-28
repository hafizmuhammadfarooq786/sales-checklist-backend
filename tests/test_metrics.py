"""
Test pipeline metrics endpoint
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_get_pipeline_metrics_authenticated(client, auth_headers):
    """Test authenticated user can access pipeline metrics"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/me/metrics",
            headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "total_sessions" in data
    assert "active_sessions" in data
    assert "completed_sessions" in data
    assert "total_opportunities" in data

    # Verify data types
    assert isinstance(data["total_sessions"], int)
    assert isinstance(data["active_sessions"], int)
    assert isinstance(data["completed_sessions"], int)
    assert isinstance(data["total_opportunities"], int)

    # Verify values are non-negative
    assert data["total_sessions"] >= 0
    assert data["active_sessions"] >= 0
    assert data["completed_sessions"] >= 0
    assert data["total_opportunities"] >= 0


@pytest.mark.asyncio
async def test_get_pipeline_metrics_unauthenticated(client):
    """Test unauthenticated user cannot access pipeline metrics"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/users/me/metrics")

    assert response.status_code == 401
