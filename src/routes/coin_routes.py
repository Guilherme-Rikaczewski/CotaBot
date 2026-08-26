from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.integrations.awesome_api import AwesomeAPIError
from src.schemas.coin_schema import CoinToCoinResponse, RealtimeQuoteResponse
from src.services.coin_service import (
    get_most_recent_conversion_registered,
    get_realtime_conversion
)


router = APIRouter(
    prefix="/coin",
    tags=["Coin"]
)


@router.get('/consult/{origin}/{target}')
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
