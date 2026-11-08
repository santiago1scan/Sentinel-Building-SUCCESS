"""Test configuration. Loaded before any test module imports the app."""
import os

# app.core.config requires DATABASE_URL at import time. The tests never open a connection,
# so a placeholder value is enough. A real value in the environment still wins.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
