import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.db.repositories.measurement_repo import MeasurementRepository
from app.db.repositories.bgp_repo import BGPRepository
from app.db.repositories.topology_repo import TopologyRepository
from app.db.repositories.incident_repo import IncidentRepository

@pytest.fixture
def mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = ["mock_data"]
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = "mock_data"
    
    session.execute = AsyncMock(return_value=mock_result)
    session.scalar = AsyncMock(return_value=1)
    return session

@pytest.mark.asyncio
async def test_measurement_repo(mock_session):
    repo = MeasurementRepository(session=mock_session)
    
    # Test get_probes
    probes = await repo.get_probes(country="US")
    assert len(probes) == 1
    
    # Test get_latency_time_series
    results, total = await repo.get_latency_time_series(
        probe_id=1,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )
    assert len(results) == 1
    assert total == 1

@pytest.mark.asyncio
async def test_bgp_repo(mock_session):
    repo = BGPRepository(session=mock_session)
    
    results, total = await repo.get_events(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        prefix="192.0.2.0/24",
        peer_asn=123
    )
    assert len(results) == 1
    assert total == 1

@pytest.mark.asyncio
async def test_topology_repo(mock_session):
    repo = TopologyRepository(session=mock_session)
    
    results, total = await repo.get_graph(asn=123, rel_type="peer")
    assert len(results) == 1
    assert total == 1

@pytest.mark.asyncio
async def test_incident_repo(mock_session):
    repo = IncidentRepository(session=mock_session)
    
    results, total = await repo.get_incidents(severity="critical", active_only=True)
    assert len(results) == 1
    assert total == 1
    
    incident = await repo.get_by_id(uuid4())
    assert incident == "mock_data"
