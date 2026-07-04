"""
RIPE Atlas API Client for NetPulse.
"""

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

class RipeAtlasClient:
    """Client for fetching data from the RIPE Atlas API."""
    
    BASE_URL = "https://atlas.ripe.net/api/v2"

    def __init__(self, timeout: float = 30.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        # Optional: Add user-agent to identify NetPulse
        self.headers = {"User-Agent": "NetPulse-Research-Client/0.1.0"}

    async def get_measurement_results(self, measurement_id: int) -> list[dict[str, Any]]:
        """
        Fetch the latest results for a given RIPE Atlas measurement ID.
        Handles rate limits (429) and standard server errors (5xx) with exponential backoff.
        """
        url = f"{self.BASE_URL}/measurements/{measurement_id}/results/"
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        return []
                        
                    elif response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning("ripe_atlas_rate_limited", msm_id=measurement_id, wait=wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                        
                    elif response.status_code >= 500:
                        wait_time = 2 ** attempt
                        logger.warning("ripe_atlas_server_error", msm_id=measurement_id, status=response.status_code)
                        await asyncio.sleep(wait_time)
                        continue
                        
                    else:
                        logger.error("ripe_atlas_error", msm_id=measurement_id, status=response.status_code)
                        response.raise_for_status()
                        
                except httpx.RequestError as e:
                    wait_time = 2 ** attempt
                    logger.warning("ripe_atlas_request_error", error=str(e), wait=wait_time)
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(wait_time)
                    
            logger.error("ripe_atlas_max_retries_exceeded", msm_id=measurement_id)
            raise RuntimeError(f"Max retries exceeded for measurement {measurement_id}")
