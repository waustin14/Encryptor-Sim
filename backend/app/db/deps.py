from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db.session import create_session_factory


@lru_cache(maxsize=1)
def _get_session_factory():
    settings = get_settings()
    return create_session_factory(settings.database_url)


def get_db_session() -> Iterator[Session]:
    session_factory = _get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
