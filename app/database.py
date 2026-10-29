"""
SQLAlchemy database setup for SQLite.
Creates the database engine and provides session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# For SQLite, check_same_thread=False allows access across multiple threads
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency generator that provides a database session for each request
    and closes it when finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
