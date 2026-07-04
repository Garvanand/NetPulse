"""
RIPE RIS Dump Client for NetPulse.
"""

import asyncio
import os
import tempfile
from typing import Any

import httpx
import mrtparse
import structlog

logger = structlog.get_logger()

class RipeRisClient:
    """Client for fetching and parsing RIPE RIS MRT dumps."""
    
    BASE_URL = "https://data.ris.ripe.net/"

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self.headers = {"User-Agent": "NetPulse-Research-Client/0.1.0"}

    async def fetch_and_parse_mrt(self, url: str) -> list[dict[str, Any]]:
        """
        Download an MRT gz or bz2 file from RIPE RIS and parse it.
        Yields BGP updates.
        """
        logger.info("ripe_ris_fetch_start", url=url)
        
        # RIS uses .gz most of the time
        suffix = ".gz" if url.endswith(".gz") else ".bz2"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            logger.info("ripe_ris_download_complete", path=temp_path)
            
            records = []
            mrt_iter = mrtparse.Reader(temp_path)
            
            count = 0
            for record in mrt_iter:
                if record.data:
                    records.append(record.data)
                    count += 1
                    if count >= 1000:
                        break
                        
            logger.info("ripe_ris_parse_complete", count=count)
            return records
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
