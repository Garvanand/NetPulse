import pytest
from app.ingestion.ripe_atlas_client import RipeAtlasClient
from app.ingestion.caida_loader import CaidaLoader
from app.ingestion.routeviews_client import RouteViewsClient
from app.ingestion.ripe_ris_client import RipeRisClient

# RIPE Atlas ping measurement for K-root DNS (ID 1030)
TEST_ATLAS_MSM_ID = 1030
# CAIDA test file
TEST_CAIDA_URL = "https://data.caida.org/datasets/as-relationships/serial-1/20231201.as-rel.txt.bz2"
# RouteViews test file (a relatively small RIB or update file)
TEST_ROUTEVIEWS_URL = "http://archive.routeviews.org/bgpdata/2024.01/UPDATES/updates.20240101.0000.bz2"
# RIPE RIS test file
TEST_RIPE_RIS_URL = "https://data.ris.ripe.net/rrc00/2024.01/updates.20240101.0000.gz"

@pytest.mark.asyncio
@pytest.mark.vcr(cassette_library_dir="tests/fixtures/cassettes")
async def test_ripe_atlas_client():
    client = RipeAtlasClient(timeout=10.0)
    results = await client.get_measurement_results(TEST_ATLAS_MSM_ID)
    assert isinstance(results, list)
    if len(results) > 0:
        assert "prb_id" in results[0]

@pytest.mark.asyncio
@pytest.mark.vcr(cassette_library_dir="tests/fixtures/cassettes")
async def test_caida_loader():
    loader = CaidaLoader(timeout=60.0)
    results = await loader.fetch_and_parse(TEST_CAIDA_URL)
    assert isinstance(results, list)
    if len(results) > 0:
        assert "as1" in results[0]
        assert "as2" in results[0]
        assert "rel" in results[0]

from unittest.mock import patch, MagicMock

async def mock_aiter_bytes(*args, **kwargs):
    yield b""

@pytest.mark.asyncio
async def test_routeviews_client():
    client = RouteViewsClient(timeout=120.0)
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.aiter_bytes = mock_aiter_bytes
        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = mock_response
        
        with patch("mrtparse.Reader") as mock_reader:
            mock_reader.return_value = []
            results = await client.fetch_and_parse_mrt(TEST_ROUTEVIEWS_URL)
            assert isinstance(results, list)

@pytest.mark.asyncio
async def test_ripe_ris_client():
    client = RipeRisClient(timeout=120.0)
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.aiter_bytes = mock_aiter_bytes
        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = mock_response
        
        with patch("mrtparse.Reader") as mock_reader:
            mock_reader.return_value = []
            results = await client.fetch_and_parse_mrt(TEST_RIPE_RIS_URL)
            assert isinstance(results, list)

@pytest.mark.asyncio
@pytest.mark.live
async def test_ripe_atlas_live():
    """Live integration test hitting the real RIPE Atlas API."""
    client = RipeAtlasClient(timeout=10.0)
    results = await client.get_measurement_results(TEST_ATLAS_MSM_ID)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "prb_id" in results[0]
