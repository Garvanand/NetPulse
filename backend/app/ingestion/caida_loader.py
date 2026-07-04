"""
CAIDA AS-Relationship Loader for NetPulse.

Attribution: 
This uses the CAIDA AS Relationships Dataset.
Citation: "The CAIDA AS Relationships Dataset, <date>"
https://www.caida.org/catalog/datasets/as-relationships/
"""

import bz2
import re
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

class CaidaLoader:
    """Client for fetching and parsing CAIDA AS-relationship datasets."""
    
    BASE_URL = "https://data.caida.org/datasets/as-relationships/serial-1/"
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {"User-Agent": "NetPulse-Research-Client/0.1.0"}
        
    async def get_latest_file_url(self) -> str:
        """Fetch the directory listing and parse out the most recent .bz2 file."""
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, verify=False) as client:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
            
            # Simple regex to find the .as-rel.txt.bz2 files
            matches = re.findall(r'href="([^"]+\.as-rel\.txt\.bz2)"', response.text)
            if not matches:
                raise ValueError("Could not find any CAIDA dataset files in directory listing.")
            
            # Sort chronologically (filenames start with YYYYMMDD)
            matches.sort()
            latest = matches[-1]
            return f"{self.BASE_URL}{latest}"

    async def fetch_and_parse(self, url: str | None = None) -> list[dict[str, Any]]:
        """
        Download and parse the CAIDA AS relationship dataset.
        Returns a list of dicts: {"as1": int, "as2": int, "rel": int}
        Where rel: -1 = provider-customer, 0 = peer-peer
        """
        if not url:
            url = await self.get_latest_file_url()
            
        logger.info("caida_fetch_start", url=url)
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            decompressed = bz2.decompress(response.content).decode("utf-8")
            
            relationships = []
            for line in decompressed.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        as1 = int(parts[0])
                        as2 = int(parts[1])
                        rel = int(parts[2])
                        relationships.append({
                            "as1": as1,
                            "as2": as2,
                            "rel": rel
                        })
                    except ValueError:
                        continue
                        
            logger.info("caida_parse_complete", count=len(relationships))
            return relationships
