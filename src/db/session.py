from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from pathlib import Path
from dotenv import load_dotenv
import os

ENV_PATH = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_pg = os.getenv("POSTGRES_DB")
db_host = os.getenv("PG_HOST")

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{db_user}:{db_password}@{db_host}:5432/{db_pg}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)


async def get_db():
    async with SessionLocal() as session:
        yield session
