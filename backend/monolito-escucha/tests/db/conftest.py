"""Shared fixtures for tests that need a real PostgreSQL (marker `db`).

They run only when TEST_DATABASE_URL points to a disposable database, for example:

    docker run -d --name sentinel-test-pg -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=sentinel_test -p 127.0.0.1:55432:5432 postgres:16-alpine
    TEST_DATABASE_URL=postgresql+asyncpg://test:test@127.0.0.1:55432/sentinel_test pytest -m db

WARNING: these tests drop and recreate every table in that database.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SERVICE_DIR = Path(__file__).resolve().parents[2]
# The console script, not `python -m alembic`: the service's own alembic/ folder would shadow the package.
ALEMBIC = shutil.which("alembic", path=str(Path(sys.executable).parent)) or "alembic"


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/db/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.db)
            if not TEST_DATABASE_URL:
                item.add_marker(pytest.mark.skip(reason="Define TEST_DATABASE_URL to run DB tests"))


def run_alembic(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL or ""}
    return subprocess.run(
        [ALEMBIC, *args],
        cwd=SERVICE_DIR, env=env, capture_output=True, text=True,
    )


def reset_schema() -> None:
    """Drop everything, then migrate from zero to head."""
    import asyncio

    import asyncpg

    async def _drop():
        conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        await conn.close()

    asyncio.run(_drop())
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr


async def areset_schema() -> None:
    """reset_schema for async fixtures (asyncio.run cannot be nested in a running loop)."""
    import asyncpg

    conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await conn.close()
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr
