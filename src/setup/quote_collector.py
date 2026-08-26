"""Coletor periódico de cotações da AwesomeAPI.

A cada `COLLECT_INTERVAL` segundos (5 minutos por padrão) consulta o preço
atual dos pares monitorados e grava em `coins`.

As três moedas são pedidas numa única requisição — a AwesomeAPI aceita
vários pares no mesmo endpoint /json/last —, então o custo é de apenas
uma chamada por ciclo.

Uso:
    python -m src.setup.quote_collector   # roda solto, fora da API
"""
import asyncio
import os
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import SessionLocal, engine
from src.integrations.awesome_api import AwesomeAPIError, get_last_quotes
from src.models.coins import Coins
from src.services.alert_service import check_alerts
from src.setup.seed_coins import SEED_ORIGINS, SEED_TARGET

# Pares monitorados — os mesmos populados pelo seed.
TRACKED_ORIGINS = SEED_ORIGINS
TRACKED_TARGET = SEED_TARGET

COLLECT_INTERVAL = float(os.getenv('QUOTE_COLLECT_INTERVAL', '300'))


async def _last_saved_timestamps(db: AsyncSession) -> dict[str, datetime]:
    """Devolve o `created_at` mais recente já gravado por moeda de origem."""
    query = (
        select(Coins.coin_name_origin, func.max(Coins.created_at))
        .where(Coins.coin_name_target == TRACKED_TARGET)
        .group_by(Coins.coin_name_origin)
    )

    result = await db.execute(query)

    return {origin: created_at for origin, created_at in result.all()}


async def collect_quotes(db: AsyncSession) -> tuple[int, int]:
    """Busca a cotação atual dos pares, grava e dispara os alertas.

    Devolve quantas cotações foram gravadas e quantos alertas dispararam.
    """
    pairs = [f'{origin}-{TRACKED_TARGET}' for origin in TRACKED_ORIGINS]

    quotes = await get_last_quotes(pairs)

    last_saved = await _last_saved_timestamps(db)

    rows: list[Coins] = []

    for pair, quote in quotes.items():
        origin = pair.split('-')[0]
        created_at = quote.timestamp.astimezone()
        previous = last_saved.get(origin)

        # Fora do horário de pregão a API repete a última cotação; sem
        # isso o banco encheria de linhas idênticas nos fins de semana.
        if previous is not None and created_at <= previous:
            continue

        rows.append(
            Coins(
                coin_name_origin=origin,
                coin_name_target=TRACKED_TARGET,
                conversion_value=str(quote.bid),
                created_at=created_at
            )
        )

    if rows:
        db.add_all(rows)
        await db.commit()

    # Os alertas são checados mesmo sem cotação nova: um alerta pode ter
    # sido cadastrado depois da última variação do par.
    messages = await check_alerts(db, quotes)

    return len(rows), len(messages)


async def run_collector() -> None:
    """Laço infinito de coleta. Encerra ao ser cancelado."""
    print(
        f'[collector] iniciado — {", ".join(TRACKED_ORIGINS)} '
        f'a cada {COLLECT_INTERVAL:.0f}s'
    )

    while True:
        try:
            async with SessionLocal() as db:
                saved, triggered = await collect_quotes(db)

            if saved or triggered:
                print(
                    f'[collector] {datetime.now():%H:%M:%S} '
                    f'-> {saved} cotações gravadas, '
                    f'{triggered} alertas disparados'
                )

        except asyncio.CancelledError:
            print('[collector] encerrado.')
            raise

        except AwesomeAPIError as error:
            print(f'[collector] AwesomeAPI indisponível: {error}')

        except Exception as error:
            # Um ciclo com erro não pode derrubar o coletor.
            print(f'[collector] erro inesperado: {error}')

        await asyncio.sleep(COLLECT_INTERVAL)


async def main() -> None:
    try:
        await run_collector()

    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
