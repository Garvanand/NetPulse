"""
RouteViews MRT Dump Client for NetPulse.
"""

import asyncio
import os
import tempfile
from typing import Any

import httpx
import mrtparse
import structlog

logger = structlog.get_logger()

class RouteViewsClient:
    """Client for fetching and parsing RouteViews MRT dumps."""
    
    BASE_URL = "http://archive.routeviews.org/bgpdata"

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self.headers = {"User-Agent": "NetPulse-Research-Client/0.1.0"}

    async def fetch_and_parse_mrt(self, url: str) -> list[dict[str, Any]]:
        """
        Download an MRT bz2 file from RouteViews and parse it.
        Yields BGP updates/RIB entries. Since MRT files can be large,
        this implementation reads into a temporary file, then parses.
        """
        logger.info("routeviews_fetch_start", url=url)
        
        fd, temp_path = tempfile.mkstemp(suffix=".bz2")
        os.close(fd)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            logger.info("routeviews_download_complete", path=temp_path)
            
            # Parse MRT file synchronously (mrtparse is synchronous)
            # In a highly scaled system, this should run in a ThreadPoolExecutor.
            records = []
            mrt_iter = mrtparse.Reader(temp_path)
            
            count = 0
            for record in mrt_iter:
                # We extract simple fields for the pipeline
                # mrtparse output can be deeply nested.
                if record.data:
                    # We just collect a small sample for the fixture/test
                    # Real production would stream these to TimescaleDB.
                    records.append(record.data)
                    count += 1
                    if count >= 1000:  # Limit for sample size
                        break
                        
            logger.info("routeviews_parse_complete", count=count)
            return records
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
