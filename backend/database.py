from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

_url = settings.database_url
# Accept Neon/Heroku-style "postgres://" and normalise to SQLAlchemy's driver URL.
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg2://", 1)

is_sqlite = _url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

if is_sqlite:
    engine = create_engine(_url, connect_args=connect_args)
else:
    # Neon/serverless Postgres drops idle conns and Render free sleeps;
    # pre_ping + recycle keep the pool healthy after wake.
    engine = create_engine(
        _url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)
