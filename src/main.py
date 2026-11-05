import asyncio
from fastapi import FastAPI
from src.db.session import engine, SessionLocal
from src.db.base import Base
from src.routes import auth_routes
from src.routes import user_routes
from src.routes import coin_routes
from src.routes import alert_routes
from src.routes import webhook
from contextlib import asynccontextmanager, suppress
from src.cache.redis_client import connection
from src.setup.quote_collector import run_collector
from src.setup.seed_coins import seed_coins
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await seed_coins(db)

    collector = asyncio.create_task(run_collector())

    yield

    collector.cancel()

    with suppress(asyncio.CancelledError):
        await collector

    await connection.aclose()


_ORIGENS_PADRAO = (
    "http://localhost:5173,http://localhost:5174,"
    "http://localhost:3000,http://localhost:8080"
)


def origens_permitidas() -> list[str]:
    bruto = os.getenv("CORS_ORIGINS", _ORIGENS_PADRAO)
    return [origem.strip() for origem in bruto.split(",") if origem.strip()]


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # A autenticação usa cookie httpOnly: o navegador só o envia entre
    # origens se `allow_credentials` estiver ligado, e isso é proibido
    # junto de "*" — daí a lista explícita.
    # allow_origins=origens_permitidas(),
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(coin_routes.router)
app.include_router(alert_routes.router)
app.include_router(webhook.router)
