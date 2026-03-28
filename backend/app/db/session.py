from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    global _engine, _session_factory

    resolved_url = database_url or get_settings().database_url
    if _engine is None or str(_engine.url) != resolved_url:
        connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
        _engine = create_engine(
            resolved_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        _session_factory = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    return _session_factory


def get_engine(database_url: str | None = None) -> Engine:
    configure_session_factory(database_url)
    assert _engine is not None
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    factory = configure_session_factory(database_url)
    assert factory is not None
    return factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
