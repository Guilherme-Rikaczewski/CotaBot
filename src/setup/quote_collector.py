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


async def _last_saved_quotes(
    db: AsyncSession
) -> dict[str, tuple[datetime, float]]:
    """Última cotação gravada de cada moeda: (created_at, valor).

    O valor é usado para detectar o cruzamento do alvo dos alertas, então
    não basta o `created_at` — é preciso a linha inteira mais recente.
    """
    row_number = func.row_number().over(
        partition_by=Coins.coin_name_origin,
        order_by=Coins.created_at.desc()
    ).label('row_number')

    subquery = (
        select(
            Coins.coin_name_origin,
            Coins.conversion_value,
            Coins.created_at,
            row_number
        )
        .where(Coins.coin_name_target == TRACKED_TARGET)
        .subquery()
    )

    query = (
        select(
            subquery.c.coin_name_origin,
            subquery.c.conversion_value,
            subquery.c.created_at
        )
        .where(subquery.c.row_number == 1)
    )

    result = await db.execute(query)

    return {
        origin: (created_at, float(value))
        for origin, value, created_at in result.all()
    }


async def collect_quotes(db: AsyncSession) -> tuple[int, int]:
    """Busca a cotação atual dos pares, grava e dispara os alertas.

    Devolve quantas cotações foram gravadas e quantos alertas dispararam.
    """
    pairs = [f'{origin}-{TRACKED_TARGET}' for origin in TRACKED_ORIGINS]

    quotes = await get_last_quotes(pairs)

    # Lido antes da gravação: são as cotações do ciclo anterior, e é a
    # comparação com elas que revela se o alvo de um alerta foi cruzado.
    last_saved = await _last_saved_quotes(db)

    rows: list[Coins] = []

    for pair, quote in quotes.items():
        origin = pair.split('-')[0]
        created_at = quote.timestamp.astimezone()
        previous = last_saved.get(origin)

        # Fora do horário de pregão a API repete a última cotação; sem
        # isso o banco encheria de linhas idênticas nos fins de semana.
        if previous is not None and created_at <= previous[0]:
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
    previous_prices = {
        origin: value
        for origin, (_, value) in last_saved.items()
    }

    messages = await check_alerts(db, quotes, previous_prices)

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
