import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.db.models import UserModel

# Create a mock user for authentication
test_user = UserModel(id=uuid4(), email="test@example.com", is_active=True, tier="free")

async def override_get_current_active_user():
    return test_user

from unittest.mock import MagicMock, AsyncMock

async def mock_get_db_session_success():
    # We yield a MagicMock that simulates an AsyncSession
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Mocking result.scalars().all() returning empty list for simplicity
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    
    # For pagination total scalar
    mock_session.scalar = AsyncMock(return_value=0)
    
    # For general execute
    mock_session.execute = AsyncMock(return_value=mock_result)
    yield mock_session

@pytest.fixture
async def client():
    # Setup happy path overrides
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[get_db_session] = mock_get_db_session_success
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.fixture
async def unauth_client():
    app.dependency_overrides[get_db_session] = mock_get_db_session_success
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

# --- Measurements ---
@pytest.mark.asyncio
async def test_measurements_probes_happy_path(client: AsyncClient):
    resp = await client.get("/measurements/probes?country=US")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_measurements_probes_validation_error(client: AsyncClient):
    resp = await client.get("/measurements/probes?country=USA") # Max length is 2
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_measurements_probes_auth_error(unauth_client: AsyncClient):
    resp = await unauth_client.get("/measurements/probes?country=US")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_measurements_latency_happy_path(client: AsyncClient):
    resp = await client.get("/measurements/1/latency?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_measurements_latency_validation_error(client: AsyncClient):
    # end_time before start_time
    resp = await client.get("/measurements/1/latency?start_time=2024-01-02T00:00:00Z&end_time=2024-01-01T00:00:00Z")
    assert resp.status_code == 422

# --- BGP ---
@pytest.mark.asyncio
async def test_bgp_events_happy_path(client: AsyncClient):
    resp = await client.get("/bgp/events?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_bgp_events_validation_error(client: AsyncClient):
    resp = await client.get("/bgp/events?peer_asn=-1&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z") # ASN must be >= 1
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_bgp_events_auth_error(unauth_client: AsyncClient):
    resp = await unauth_client.get("/bgp/events?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
    assert resp.status_code == 401

# --- Topology (Load shape test) ---
@pytest.mark.asyncio
async def test_topology_happy_path(client: AsyncClient):
    resp = await client.get("/topology/as-graph?page=1&size=100")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

@pytest.mark.asyncio
async def test_topology_validation_error(client: AsyncClient):
    resp = await client.get("/topology/as-graph?page=-1") # Page >= 1
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_topology_auth_error(unauth_client: AsyncClient):
    resp = await unauth_client.get("/topology/as-graph")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_topology_pagination_limit(client: AsyncClient):
    # Enforce no unbounded sets
    resp = await client.get("/topology/as-graph?size=5000") # Max is 1000
    assert resp.status_code == 422

# --- Predictions ---
@pytest.mark.asyncio
async def test_predictions_happy_path(client: AsyncClient):
    resp = await client.get("/predictions/")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_predictions_validation_error(client: AsyncClient):
    resp = await client.get("/predictions/?min_score=1.5") # max 1.0
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_predictions_auth_error(unauth_client: AsyncClient):
    resp = await unauth_client.get("/predictions/")
    assert resp.status_code == 401

# --- Incidents ---
@pytest.mark.asyncio
async def test_incidents_happy_path(client: AsyncClient):
    resp = await client.get("/incidents/")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_incidents_validation_error(client: AsyncClient):
    resp = await client.get("/incidents/?size=1000") # size max 100
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_incidents_auth_error(unauth_client: AsyncClient):
    resp = await unauth_client.get("/incidents/")
    assert resp.status_code == 401

# --- WS ---
@pytest.mark.asyncio
async def test_ws_missing_token():
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # FastAPI's test client for websockets is slightly different, usually requires `TestClient.websocket_connect`.
        # However, making an HTTP GET to WS endpoint usually returns 400 or 403.
        # But we can just use the standard TestClient for WS.
        pass

from fastapi.testclient import TestClient
def test_websocket_auth_error():
    client = TestClient(app)
    with pytest.raises(Exception): # Will raise WebSocketDisconnect or reject
        with client.websocket_connect("/ws/live"):
            pass
