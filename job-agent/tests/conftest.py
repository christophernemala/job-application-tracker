"""Shared test fixtures."""

import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database and patch get_db_path everywhere."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)

    # Patch in both modules that import get_db_path
    import src.utils.config_loader as cl
    import src.storage.database as db_mod

    monkeypatch.setattr(cl, "get_db_path", lambda: db_path)
    monkeypatch.setattr(db_mod, "get_db_path", lambda: db_path)

    from src.storage.database import init_database
    init_database(db_path)

    return db_path
