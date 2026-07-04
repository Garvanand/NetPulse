from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class ASRelationshipModel(Base):
    """AS-to-AS relationship graph from CAIDA dataset."""

    __tablename__ = "as_relationships"

    asn_a: Mapped[int] = mapped_column(Integer, primary_key=True)
    asn_b: Mapped[int] = mapped_column(Integer, primary_key=True)
    rel_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'customer', 'peer', 'provider'
    source: Mapped[str] = mapped_column(String(30), default="caida-serial2")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        # Edge lookups are indexed in both directions:
        # PK covers asn_a -> asn_b. We explicitly add asn_b for reverse lookup.
        Index("ix_as_relationships_asn_b", "asn_b"),
    )

class ASMetadataModel(Base):
    """AS metadata: names, organizations, countries. Normalized reference table."""

    __tablename__ = "as_metadata"

    asn: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    cone_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
