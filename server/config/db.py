from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
from .settings import settings

# PgBouncer transaction-mode pooling configuration
# IMPORTANT: When using PgBouncer in transaction mode, we must:
# 1. Use NullPool to avoid double-pooling (PgBouncer already pools connections)
# 2. Disable prepared statement caching to avoid issues with transaction boundaries
#    (PgBouncer transaction mode doesn't support prepared statements across transactions)
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # PgBouncer handles pooling, disable SQLAlchemy's pool
    echo=settings.DEBUG,
    # Disable prepared statement caching for PgBouncer transaction mode
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    } if "postgresql" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
