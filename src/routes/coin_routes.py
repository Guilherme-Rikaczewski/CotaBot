from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.coin_schema import CoinToCoinResponse
from src.services.coin_service import (
    get_most_recent_conversion_registered
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
