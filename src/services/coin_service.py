from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.coins import Coins


async def get_most_recent_conversion_registered(
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
