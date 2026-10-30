from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from src.integrations.awesome_api import get_last_quote
from src.models.coins import Coins
from src.schemas.quote_schema import Quote
from src.schemas.coin_schema import Interval, CointAtInterval
from src.utils.money import format_conversion


async def get_last_conversion_registered(
    db: AsyncSession,
    origin: str,
    target: str
) -> float:
    query = (
        select(Coins.conversion_value)
        .where(
            Coins.coin_name_origin == origin,
            Coins.coin_name_target == target
        )
        .order_by(Coins.created_at.desc())
        .limit(1)
    )

    result = await db.execute(query)

    conversion = result.scalar_one_or_none()

    if conversion is None:
        raise ValueError("Conversion not found")

    return float(conversion)


async def get_last_24_hours_conversions_registered(
    db: AsyncSession,
    origin: str,
    target: str
) -> list[dict]:

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    query = (
        select(
            Coins.conversion_value,
            Coins.created_at
        )
        .where(
            Coins.coin_name_origin == origin,
            Coins.coin_name_target == target,
            Coins.created_at >= day_ago,
        )
        .order_by(Coins.created_at.asc())
    )

    result = await db.execute(query)

    conversions = result.all()

    return [
        {
            "conversion_value": float(conversion),
            "created_at": created_at
        }
        for conversion, created_at in conversions
    ]


async def get_conversions_registered_in_x_days_with_y_interval(
    db: AsyncSession,
    origin: str,
    target: str,
    days: int,
    interval: Interval
) -> list[CointAtInterval]:

    now = datetime.now(timezone.utc)
    time_ago = now - timedelta(days=days)

    time_interval = func.date_trunc(
        interval.value,
        Coins.created_at
    )

    row_number = func.row_number().over(
        partition_by=time_interval,
        order_by=Coins.created_at.desc()
    ).label("row_number")

    subquery = (
        select(
            Coins.conversion_value,
            Coins.created_at,
            row_number
        )
        .where(
            Coins.coin_name_origin == origin,
            Coins.coin_name_target == target,
            Coins.created_at >= time_ago,
        )
        .subquery()
    )

    query = (
        select(
            subquery.c.conversion_value,
            subquery.c.created_at
        )
        .where(
            subquery.c.row_number == 1
        )
        .order_by(
            subquery.c.created_at.asc()
        )
    )

    result = await db.execute(query)
    conversions = result.all()

    return [
        {
            "conversion_value": float(conversion),
            "created_at": created_at
        }
        for conversion, created_at in conversions
    ]


async def get_realtime_conversion(
    db: AsyncSession,
    origin: str,
    target: str,
    persist: bool = True
) -> Quote:
    """Consulta o preço atual do par direto na AwesomeAPI.

    Por padrão a cotação também é gravada em `coins`, mantendo o
    histórico do banco atualizado a cada consulta.
    """
    quote = await get_last_quote(origin, target)

    if persist:
        db.add(
            Coins(
                coin_name_origin=origin.strip().upper(),
                coin_name_target=target.strip().upper(),
                conversion_value=format_conversion(quote.bid),
                created_at=quote.timestamp.astimezone()
            )
        )

        await db.commit()

    return quote


# O produto é cotado em real, então "o dia" é o dia de Brasília — e não
# o do relógio do servidor, que roda em UTC.
DAILY_TIMEZONE = ZoneInfo('America/Sao_Paulo')


async def get_daily_summary(
    db: AsyncSession,
    origins: Sequence[str],
    target: str = 'BRL'
) -> list[dict]:
    """Abertura, última cotação e variação do dia de cada moeda.

    Lê apenas o que o coletor já gravou em `coins`: a primeira e a
    última cotação do dia por moeda. Moedas sem registro hoje (fim de
    semana, feriado) saem com `opening` e `closing` nulos.
    """
    now = datetime.now(DAILY_TIMEZONE)

    start_of_day = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    first = func.row_number().over(
        partition_by=Coins.coin_name_origin,
        order_by=Coins.created_at.asc()
    ).label('first_of_day')

    last = func.row_number().over(
        partition_by=Coins.coin_name_origin,
        order_by=Coins.created_at.desc()
    ).label('last_of_day')

    subquery = (
        select(
            Coins.coin_name_origin,
            Coins.conversion_value,
            Coins.created_at,
            first,
            last
        )
        .where(
            Coins.coin_name_origin.in_(origins),
            Coins.coin_name_target == target,
            Coins.created_at >= start_of_day
        )
        .subquery()
    )

    # Duas linhas por moeda, no máximo: a primeira e a última.
    query = select(
        subquery.c.coin_name_origin,
        subquery.c.conversion_value,
        subquery.c.created_at,
        subquery.c.first_of_day,
        subquery.c.last_of_day
    ).where(
        (subquery.c.first_of_day == 1) | (subquery.c.last_of_day == 1)
    )

    result = await db.execute(query)

    opening: dict[str, float] = {}
    closing: dict[str, float] = {}
    updated: dict[str, datetime] = {}

    for origin, value, created_at, is_first, is_last in result.all():
        if is_first == 1:
            opening[origin] = float(value)

        if is_last == 1:
            closing[origin] = float(value)
            updated[origin] = created_at

    summary: list[dict] = []

    for origin in origins:
        open_value = opening.get(origin)
        close_value = closing.get(origin)

        variation = None

        if open_value and close_value:
            variation = (close_value - open_value) / open_value * 100

        summary.append({
            'coin': origin,
            'target': target,
            'opening': open_value,
            'closing': close_value,
            'variation': variation,
            'updated_at': updated.get(origin)
        })

    return summary
