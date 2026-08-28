from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.integrations.awesome_api import AwesomeAPIError
from src.schemas.coin_schema import (
    CoinToCoinResponse,
    RealtimeQuoteResponse,
    Interval,
    CoinToCoinPeriodResponse
)
from src.services.coin_service import (
    get_most_recent_conversion_registered,
    get_realtime_conversion,
    get_conversions_registered_in_x_days_with_y_interval
)


router = APIRouter(
    prefix="/coin",
    tags=["Coin"]
)


@router.get('/conversion/{origin}/{target}')
async def get_conversion(
    origin: str,
    target: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        if not origin or not target:
            raise HTTPException(
                400,
                detail='Invalid coins'
            )

        conversion = await get_most_recent_conversion_registered(
            db, origin, target
        )

        return CoinToCoinResponse(
            conversion=conversion
        )

    except Exception as error:
        raise HTTPException(
            500,
            detail=f'Internal server error: {error}'
        )


@router.get('/period/{origin}/{target}/{days}/{interval}')
async def get_conversions_at_interval(
    origin: str,
    target: str,
    days: int,
    interval: Interval,
    db: AsyncSession = Depends(get_db)
):
    try:
        if not origin or not target or not days or not interval:
            raise HTTPException(
                400,
                detail='Invalid coins'
            )

        rates = await get_conversions_registered_in_x_days_with_y_interval(
            db,
            origin,
            target,
            days,
            interval
        )

        return CoinToCoinPeriodResponse(
            conversions=rates
        )

    except Exception as error:
        raise HTTPException(
            500,
            detail=f'Internal server error: {error}'
        )


@router.get(
    '/realtime/{origin}/{target}',
    response_model=RealtimeQuoteResponse,
    summary='Cotação em tempo real direto da AwesomeAPI'
)
async def get_realtime_quote(
    origin: str,
    target: str,
    db: AsyncSession = Depends(get_db)
):
    if not origin or not target:
        raise HTTPException(
            400,
            detail='Invalid coins'
        )

    try:
        quote = await get_realtime_conversion(db, origin, target)

    except ValueError as error:
        raise HTTPException(
            400,
            detail=str(error)
        )

    except AwesomeAPIError as error:
        raise HTTPException(
            502,
            detail=f'Quote provider unavailable: {error}'
        )

    return RealtimeQuoteResponse(
        origin=quote.code or origin.upper(),
        target=quote.codein or target.upper(),
        conversion=quote.bid,
        high=quote.high,
        low=quote.low,
        pct_change=quote.pct_change,
        updated_at=quote.timestamp
    )
