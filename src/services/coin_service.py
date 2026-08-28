from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from src.integrations.awesome_api import get_last_quote
from src.models.coins import Coins
from src.schemas.quote_schema import Quote
from src.schemas.coin_schema import Interval


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
) -> list[dict]:

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
                conversion_value=str(quote.bid),
                created_at=quote.timestamp.astimezone()
            )
        )

        await db.commit()

    return quote
