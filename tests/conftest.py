"""
Pytest configuration and shared fixtures for DevPilot test suite.
"""
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from devpilot.api.app import app
from devpilot.config import settings
from devpilot.db.database import Database


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database for testing."""
    db_file = tmp_path / "test_devpilot.sqlite3"
    db = Database(db_path=db_file)
    return db


@pytest.fixture
def temp_repo(tmp_path):
    """Copies sample_repo into an isolated temporary directory for non-destructive tests."""
    repo_src = settings.DEFAULT_REPO_ROOT
    repo_copy = tmp_path / "sample_repo"
    shutil.copytree(repo_src, repo_copy)
    return repo_copy


@pytest.fixture
def api_client():
    """FastAPI TestClient fixture."""
    return TestClient(app)
