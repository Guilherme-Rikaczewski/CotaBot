from fastapi import FastAPI
from src.db.session import engine
from src.db.base import Base
from src.routes import auth_routes
from contextlib import asynccontextmanager
from src.cache.redis_client import connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await connection.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_routes.router)
