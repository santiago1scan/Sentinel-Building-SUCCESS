"""Test configuration. Loaded before any test module imports the app."""
import os

# app.core.config requires DATABASE_URL at import time. These tests never open a connection.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
