import subprocess
import os
import pytest

def test_alembic_upgrade_head_sql():
    """
    Test that Alembic can successfully generate the offline SQL for the upgrade migration.
    This proves that the SQLAlchemy models and migration scripts are syntactically valid
    and can compile down to PostgreSQL DDL.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Run alembic in offline mode to generate the SQL
    result = subprocess.run(
        [os.path.join(".venv", "Scripts", "alembic.exe"), "upgrade", "head", "--sql"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Alembic upgrade failed:\n{result.stderr}"
    
    # Verify TimescaleDB specific raw SQL is injected
    assert "create_hypertable('probe_measurements', 'time'" in result.stdout
    assert "create_hypertable('bgp_events', 'time'" in result.stdout

def test_alembic_downgrade_base_sql():
    """
    Test that Alembic can successfully generate the offline SQL for the downgrade migration.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Run alembic in offline mode to generate the SQL for downgrade
    # We specify the specific revision to downgrade from since 'head' might not be recognized offline for downgrade
    result = subprocess.run(
        [os.path.join(".venv", "Scripts", "alembic.exe"), "downgrade", "5a0f73372232:base", "--sql"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Alembic downgrade failed:\n{result.stderr}"
    
    # Verify TimescaleDB specific raw SQL drop is injected
    assert "remove_retention_policy('probe_measurements'" in result.stdout
