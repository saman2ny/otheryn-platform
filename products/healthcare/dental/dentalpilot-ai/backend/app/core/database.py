from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def build_engine():
    url = make_url(settings.database_url)
    connect_args = {"check_same_thread": False} if url.drivername.startswith("sqlite") else {}
    # pool_pre_ping avoids stale connections after container restarts.
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
