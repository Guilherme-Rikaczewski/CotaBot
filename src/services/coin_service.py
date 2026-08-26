from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.integrations.awesome_api import get_last_quote
from src.models.coins import Coins
from src.schemas.quote_schema import Quote


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
