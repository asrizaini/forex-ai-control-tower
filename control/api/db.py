from __future__ import annotations

import os
from collections.abc import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    if postgres_password:
        password = quote_plus(postgres_password)
        return f"postgresql+psycopg://forex_ai:{password}@127.0.0.1:5432/forex_ai"
    return "sqlite:///./forex_ai_control.db"


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def configure_database(url: str) -> None:
    global engine, SessionLocal
    engine.dispose()
    engine = create_engine(url, pool_pre_ping=True)
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
