"""Initial schema — all core tables and TimescaleDB hypertables.

Revision ID: 0001
Revises: None
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, INET, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable TimescaleDB extension ────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # ── Probes ──────────────────────────────────────────────────
    op.create_table(
        "probes",
        sa.Column("probe_id", sa.Integer(), primary_key=True),
        sa.Column("asn", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_probes_asn", "probes", ["asn"])
    op.create_index("ix_probes_country", "probes", ["country"])

    # ── Probe Measurements (TimescaleDB hypertable) ─────────────
    op.create_table(
        "probe_measurements",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("probe_id", sa.Integer(), nullable=False),
        sa.Column("target_ip", INET(), nullable=True),
        sa.Column("measurement_type", sa.String(20), nullable=True),
        sa.Column("rtt_ms", sa.Double(), nullable=True),
        sa.Column("packet_loss", sa.Double(), nullable=True),
        sa.Column("asn_src", sa.Integer(), nullable=True),
        sa.Column("asn_dst", sa.Integer(), nullable=True),
        sa.Column("country_src", sa.String(2), nullable=True),
        sa.Column("country_dst", sa.String(2), nullable=True),
        sa.Column("raw_json", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("time", "probe_id"),
    )
    op.create_index(
        "ix_probe_measurements_probe_time",
        "probe_measurements",
        ["probe_id", "time"],
    )
    op.create_index(
        "ix_probe_measurements_asn_src", "probe_measurements", ["asn_src"]
    )
    op.create_index(
        "ix_probe_measurements_asn_dst", "probe_measurements", ["asn_dst"]
    )
    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('probe_measurements', 'time', "
        "if_not_exists => TRUE);"
    )

    # ── BGP Events (TimescaleDB hypertable) ─────────────────────
    op.create_table(
        "bgp_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("collector", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("prefix", CIDR(), nullable=True),
        sa.Column("peer_asn", sa.Integer(), nullable=True),
        sa.Column("origin_asn", sa.Integer(), nullable=True),
        sa.Column("as_path", ARRAY(sa.Integer()), nullable=True),
        sa.Column("communities", ARRAY(sa.Integer(), dimensions=2), nullable=True),
        sa.Column("raw_json", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("time", "id"),
    )
    op.create_index("ix_bgp_events_event_type", "bgp_events", ["event_type"])
    op.create_index("ix_bgp_events_peer_asn", "bgp_events", ["peer_asn"])
    op.create_index("ix_bgp_events_origin_asn", "bgp_events", ["origin_asn"])
    op.create_index(
        "ix_bgp_events_origin_time", "bgp_events", ["origin_asn", "time"]
    )
    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('bgp_events', 'time', "
        "if_not_exists => TRUE);"
    )

    # ── AS Relationships ────────────────────────────────────────
    op.create_table(
        "as_relationships",
        sa.Column("asn_a", sa.Integer(), nullable=False),
        sa.Column("asn_b", sa.Integer(), nullable=False),
        sa.Column("rel_type", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), server_default="caida-serial2"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("asn_a", "asn_b"),
    )
    op.create_index("ix_as_relationships_asn_b", "as_relationships", ["asn_b"])

    # ── AS Metadata ─────────────────────────────────────────────
    op.create_table(
        "as_metadata",
        sa.Column("asn", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("org", sa.String(255), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("cone_size", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_as_metadata_country", "as_metadata", ["country"])

    # ── Incidents ───────────────────────────────────────────────
    op.create_table(
        "incidents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("incident_type", sa.String(30), nullable=False),
        sa.Column("affected_asns", ARRAY(sa.Integer()), nullable=True),
        sa.Column("affected_prefixes", ARRAY(CIDR()), nullable=True),
        sa.Column("prediction_score", sa.Double(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
    )
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_incident_type", "incidents", ["incident_type"])


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_table("as_metadata")
    op.drop_table("as_relationships")
    op.drop_table("bgp_events")
    op.drop_table("probe_measurements")
    op.drop_table("probes")
