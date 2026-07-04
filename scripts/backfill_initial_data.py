"""
NetPulse — Data Backfill Script

Populates the database with an initial slice of real data from:
- RIPE Atlas (ping measurements)
- RouteViews / RIPE RIS (BGP updates)
- CAIDA (AS relationships)
"""

import asyncio
import os
import sys

# Add backend to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from datetime import datetime, timezone
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.db.models import Base, ASRelationshipModel, ProbeMeasurementModel, BGPEventModel, ProbeModel
from app.ingestion.ripe_atlas_client import RipeAtlasClient
from app.ingestion.caida_loader import CaidaLoader
from app.ingestion.routeviews_client import RouteViewsClient

logger = structlog.get_logger()

async def init_db(engine):
    """Ensure provisional tables exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def backfill():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    await init_db(engine)
    
    logger.info("backfill_started")
    
    # 1. Backfill CAIDA AS Relationships
    logger.info("backfilling_caida")
    caida = CaidaLoader()
    try:
        relationships = await caida.fetch_and_parse()
        async with session_factory() as session:
            for rel in relationships[:500]:
                db_rel = ASRelationshipModel(
                    asn_a=rel["as1"],
                    asn_b=rel["as2"],
                    rel_type=str(rel["rel"]),
                    source="caida",
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(db_rel)
            await session.commit()
    except Exception as e:
        logger.error("caida_backfill_failed", error=str(e))
        
    # 2. Backfill RIPE Atlas
    logger.info("backfilling_ripe_atlas")
    atlas = RipeAtlasClient()
    try:
        measurements = await atlas.get_measurement_results(1030)
        async with session_factory() as session:
            for m in measurements[:200]:
                probe_id = m.get("prb_id")
                # Add probe if missing
                session.add(ProbeModel(
                    probe_id=probe_id,
                    updated_at=datetime.now(timezone.utc)
                ))
                
                db_m = ProbeMeasurementModel(
                    time=datetime.fromtimestamp(m.get("timestamp", 0), tz=timezone.utc),
                    probe_id=probe_id,
                    target_ip="193.0.14.129",
                    measurement_type="ping",
                    rtt_ms=m.get("min", 0.0) if m.get("min") else -1.0,
                    packet_loss=0.0
                )
                session.add(db_m)
            await session.commit()
    except Exception as e:
        logger.error("ripe_atlas_backfill_failed", error=str(e))
        
    # 3. Backfill RouteViews
    logger.info("backfilling_routeviews")
    rv = RouteViewsClient()
    try:
        url = "http://archive.routeviews.org/bgpdata/2024.01/UPDATES/updates.20240101.0000.bz2"
        records = await rv.fetch_and_parse_mrt(url)
        
        async with session_factory() as session:
            for r in records[:500]:
                peer_as = r.get("peer_as")
                prefix = None
                
                bgp_msg = r.get("bgp_message", {})
                nlri = bgp_msg.get("nlri")
                if nlri and len(nlri) > 0:
                    prefix = f"{nlri[0].get('prefix')}/{nlri[0].get('length')}"
                    
                db_bgp = BGPEventModel(
                    time=datetime.now(timezone.utc), 
                    collector="routeviews",
                    event_type="update",
                    prefix=prefix or "0.0.0.0/0",
                    peer_as=int(peer_as) if peer_as else 0,
                    as_path=[], 
                )
                session.add(db_bgp)
            await session.commit()
    except Exception as e:
        logger.error("routeviews_backfill_failed", error=str(e))
        
    logger.info("backfill_completed")

if __name__ == "__main__":
    asyncio.run(backfill())
