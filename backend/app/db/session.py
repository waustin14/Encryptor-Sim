from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def ensure_sqlite_permissions(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    if not url.database or url.database == ":memory:":
        return

    db_path = Path(url.database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()
    db_path.chmod(0o600)


def get_engine(database_url: str, **kwargs: Any):
    ensure_sqlite_permissions(database_url)
    return create_engine(database_url, future=True, **kwargs)


def create_session_factory(database_url: str):
    engine = get_engine(database_url, connect_args={"check_same_thread": False})
    return sessionmaker(bind=engine, expire_on_commit=False)
