"""Popula a tabela `coins` com o histórico de cotações da AwesomeAPI.

O script só age quando a tabela está vazia, então pode ser executado a
cada boot da aplicação sem duplicar registros.

A AwesomeAPI devolve no máximo 360 fechamentos por requisição, então o
histórico é varrido em janelas de 360 dias para trás — a partir de hoje —
até a API parar de responder com dados. Entre uma requisição e outra é
respeitado um intervalo para não estourar a cota do plano.

Uso:
    python -m src.setup.seed_coins
"""
import asyncio
import os
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base
from src.db.session import SessionLocal, engine
from src.integrations.awesome_api import (
    MAX_HISTORY_DAYS,
    AwesomeAPIError,
    get_quote_history_range
)
from src.models.coins import Coins
from src.schemas.quote_schema import Quote

# Moedas de origem populadas, sempre convertidas para BRL.
SEED_ORIGINS = ('USD', 'EUR', 'BTC')
SEED_TARGET = 'BRL'

# Intervalo mínimo entre requisições. O limite da AwesomeAPI é de cota
# mensal, não por segundo, então 1s já é folgado para o backfill.
REQUEST_INTERVAL = float(os.getenv('SEED_REQUEST_INTERVAL', '1'))

# Data mais antiga que faz sentido pedir — a AwesomeAPI não tem série
# anterior a isso para nenhum dos pares populados.
HISTORY_FLOOR = date(1994, 1, 1)

# Quantas janelas seguidas sem dados até considerar que a série acabou.
# Mais de uma porque pares novos (BTC) podem ter buracos no início.
MAX_EMPTY_WINDOWS = 2


async def is_database_empty(db: AsyncSession) -> bool:
    """Indica se ainda não existe nenhuma cotação registrada."""
    result = await db.execute(select(func.count()).select_from(Coins))

    return result.scalar_one() == 0


def _to_row(quote: Quote, origin: str, target: str) -> Coins:
    created_at = quote.create_date or quote.timestamp

    # A coluna é timestamptz; datetimes ingênuos assumem o fuso local.
    if created_at.tzinfo is None:
        created_at = created_at.astimezone()

    return Coins(
        coin_name_origin=origin,
        coin_name_target=target,
        conversion_value=str(quote.bid),
        created_at=created_at
    )


async def _fetch_full_history(origin: str, target: str) -> list[Coins]:
    """Varre o histórico completo de um par, do mais recente ao mais antigo."""
    rows: list[Coins] = []
    seen_days: set[date] = set()

    end_date = date.today()
    empty_windows = 0

    while end_date >= HISTORY_FLOOR and empty_windows < MAX_EMPTY_WINDOWS:
        start_date = max(
            end_date - timedelta(days=MAX_HISTORY_DAYS - 1),
            HISTORY_FLOOR
        )

        try:
            quotes = await get_quote_history_range(
                origin, target, start_date, end_date
            )

        except AwesomeAPIError as error:
            print(
                f'[seed] {origin}-{target}: falha em '
                f'{start_date:%Y-%m-%d}..{end_date:%Y-%m-%d} — {error}'
            )
            break

        if quotes:
            empty_windows = 0

            for quote in quotes:
                day = quote.timestamp.date()

                # A API repete o fechamento nas bordas das janelas.
                if day in seen_days:
                    continue

                seen_days.add(day)
                rows.append(_to_row(quote, origin, target))

        else:
            empty_windows += 1

        print(
            f'[seed] {origin}-{target}: '
            f'{start_date:%Y-%m-%d}..{end_date:%Y-%m-%d} '
            f'-> {len(quotes)} cotações (total {len(rows)})'
        )

        if start_date == HISTORY_FLOOR:
            break

        end_date = start_date - timedelta(days=1)

        await asyncio.sleep(REQUEST_INTERVAL)

    return rows


async def seed_coins(db: AsyncSession) -> int:
    """Popula a tabela `coins` caso ela esteja vazia.

    Devolve a quantidade de cotações inseridas.
    """
    if not await is_database_empty(db):
        print('[seed] banco já populado, nada a fazer.')

        return 0

    total = 0

    for index, origin in enumerate(SEED_ORIGINS):
        if index:
            await asyncio.sleep(REQUEST_INTERVAL)

        rows = await _fetch_full_history(origin, SEED_TARGET)

        if not rows:
            print(f'[seed] {origin}-{SEED_TARGET}: nenhuma cotação obtida.')
            continue

        db.add_all(rows)
        await db.commit()

        total += len(rows)

        print(
            f'[seed] {origin}-{SEED_TARGET}: {len(rows)} cotações gravadas '
            f'({min(r.created_at for r in rows):%Y-%m-%d} em diante).'
        )

    print(f'[seed] concluído: {total} cotações inseridas.')

    return total


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await seed_coins(db)

    await engine.dispose()


if __name__ == '__main__':
    started_at = datetime.now()

    asyncio.run(main())

    print(f'[seed] tempo total: {datetime.now() - started_at}')
