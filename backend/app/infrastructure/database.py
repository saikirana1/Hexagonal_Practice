from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.infrastructure.config import get_settings


def database_url_for_sqlalchemy(database_url: str) -> str:
    """Convert Neon URLs to SQLAlchemy's psycopg dialect when needed."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


engine = create_engine(database_url_for_sqlalchemy(get_settings().database_url), pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
