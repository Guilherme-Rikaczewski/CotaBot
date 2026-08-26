import asyncio
from fastapi import FastAPI
from src.db.session import engine
from src.db.base import Base
from src.routes import auth_routes
from src.routes import user_routes
from src.routes import coin_routes
from src.routes import alert_routes
from contextlib import asynccontextmanager, suppress
from src.cache.redis_client import connection
from src.setup.quote_collector import run_collector


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    collector = asyncio.create_task(run_collector())

    yield

    collector.cancel()

    with suppress(asyncio.CancelledError):
        await collector

    await connection.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(coin_routes.router)
app.include_router(alert_routes.router)
