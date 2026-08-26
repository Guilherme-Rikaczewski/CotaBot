from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.coins import Coins
from datetime import datetime, timedelta, timezone


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


async def get_last_week_conversions_registered(
    db: AsyncSession,
    origin: str,
    target: str
) -> list[dict]:

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    hour = func.date_trunc(
        "hour",
        Coins.created_at
    )

    row_number = func.row_number().over(
        partition_by=hour,
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
            Coins.created_at >= week_ago,
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
