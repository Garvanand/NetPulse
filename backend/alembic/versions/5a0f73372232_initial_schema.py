"""Initial schema

Revision ID: 5a0f73372232
Revises: 
Create Date: 2026-07-04 11:47:25.549014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5a0f73372232'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # probes
    op.create_table(
        'probes',
        sa.Column('probe_id', sa.Integer(), nullable=False),
        sa.Column('asn', sa.Integer(), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('latitude', sa.Double(), nullable=True),
        sa.Column('longitude', sa.Double(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('probe_id')
    )
    op.create_index(op.f('ix_probes_asn'), 'probes', ['asn'], unique=False)
    op.create_index(op.f('ix_probes_country'), 'probes', ['country'], unique=False)

    # probe_measurements
    op.create_table(
        'probe_measurements',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('probe_id', sa.Integer(), nullable=False),
        sa.Column('target_ip', postgresql.INET(), nullable=True),
        sa.Column('measurement_type', sa.String(length=20), nullable=True),
        sa.Column('rtt_ms', sa.Double(), nullable=True),
        sa.Column('packet_loss', sa.Double(), nullable=True),
        sa.Column('asn_src', sa.Integer(), nullable=True),
        sa.Column('asn_dst', sa.Integer(), nullable=True),
        sa.Column('country_src', sa.String(length=2), nullable=True),
        sa.Column('country_dst', sa.String(length=2), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('time', 'probe_id')
    )
    op.create_index('ix_probe_measurements_probe_time', 'probe_measurements', ['probe_id', 'time'], unique=False)
    op.create_index('ix_probe_measurements_asn_src', 'probe_measurements', ['asn_src'], unique=False)
    op.create_index('ix_probe_measurements_asn_dst', 'probe_measurements', ['asn_dst'], unique=False)
    
    # TimescaleDB hypertable for probe_measurements
    op.execute("SELECT create_hypertable('probe_measurements', 'time', if_not_exists => TRUE);")
    op.execute("SELECT add_retention_policy('probe_measurements', INTERVAL '30 days', if_not_exists => TRUE);")

    # bgp_events
    op.create_table(
        'bgp_events',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('collector', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('prefix', postgresql.CIDR(), nullable=True),
        sa.Column('peer_asn', sa.Integer(), nullable=True),
        sa.Column('origin_asn', sa.Integer(), nullable=True),
        sa.Column('as_path', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('communities', postgresql.ARRAY(sa.Integer(), dimensions=2), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('time', 'id')
    )
    op.create_index(op.f('ix_bgp_events_event_type'), 'bgp_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_bgp_events_origin_asn'), 'bgp_events', ['origin_asn'], unique=False)
    op.create_index(op.f('ix_bgp_events_peer_asn'), 'bgp_events', ['peer_asn'], unique=False)
    op.create_index('ix_bgp_events_origin_time', 'bgp_events', ['origin_asn', 'time'], unique=False)

    # TimescaleDB hypertable for bgp_events
    op.execute("SELECT create_hypertable('bgp_events', 'time', if_not_exists => TRUE);")
    op.execute("SELECT add_retention_policy('bgp_events', INTERVAL '90 days', if_not_exists => TRUE);")

    # as_relationships
    op.create_table(
        'as_relationships',
        sa.Column('asn_a', sa.Integer(), nullable=False),
        sa.Column('asn_b', sa.Integer(), nullable=False),
        sa.Column('rel_type', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('asn_a', 'asn_b')
    )
    op.create_index('ix_as_relationships_asn_b', 'as_relationships', ['asn_b'], unique=False)

    # as_metadata
    op.create_table(
        'as_metadata',
        sa.Column('asn', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('org', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('cone_size', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('asn')
    )
    op.create_index(op.f('ix_as_metadata_country'), 'as_metadata', ['country'], unique=False)

    # incidents
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('incident_type', sa.String(length=30), nullable=False),
        sa.Column('affected_asns', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('affected_prefixes', postgresql.ARRAY(postgresql.CIDR()), nullable=True),
        sa.Column('prediction_score', sa.Double(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('incident_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incidents_detected_at'), 'incidents', ['detected_at'], unique=False)
    op.create_index(op.f('ix_incidents_incident_type'), 'incidents', ['incident_type'], unique=False)
    op.create_index(op.f('ix_incidents_severity'), 'incidents', ['severity'], unique=False)

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # api_keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    op.execute("SELECT remove_retention_policy('probe_measurements', if_exists => TRUE);")
    op.execute("SELECT remove_retention_policy('bgp_events', if_exists => TRUE);")
    op.drop_index(op.f('ix_api_keys_user_id'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_incidents_severity'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_incident_type'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_detected_at'), table_name='incidents')
    op.drop_table('incidents')
    op.drop_index(op.f('ix_as_metadata_country'), table_name='as_metadata')
    op.drop_table('as_metadata')
    op.drop_index('ix_as_relationships_asn_b', table_name='as_relationships')
    op.drop_table('as_relationships')
    op.drop_index('ix_bgp_events_origin_time', table_name='bgp_events')
    op.drop_index(op.f('ix_bgp_events_peer_asn'), table_name='bgp_events')
    op.drop_index(op.f('ix_bgp_events_origin_asn'), table_name='bgp_events')
    op.drop_index(op.f('ix_bgp_events_event_type'), table_name='bgp_events')
    op.drop_table('bgp_events')
    op.drop_index('ix_probe_measurements_asn_dst', table_name='probe_measurements')
    op.drop_index('ix_probe_measurements_asn_src', table_name='probe_measurements')
    op.drop_index('ix_probe_measurements_probe_time', table_name='probe_measurements')
    op.drop_table('probe_measurements')
    op.drop_index(op.f('ix_probes_country'), table_name='probes')
    op.drop_index(op.f('ix_probes_asn'), table_name='probes')
    op.drop_table('probes')
