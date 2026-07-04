"""
NetPulse — Test suite for the health check endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint returns service identity."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NetPulse"
    assert "version" in data
    assert "tagline" in data


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    """
    Test health endpoint returns 200.
    Note: In CI without a real DB/Redis, this may return 'degraded' status
    but should still respond with 200.
    """
    response = await client.get("/health")
    # Health endpoint should always return 200 (even if degraded)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "checks" in data
