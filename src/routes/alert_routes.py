from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.integrations.awesome_api import AwesomeAPIError
from src.schemas.alert_schema import (
    AlertCreate,
    AlertResponse,
    MessageResponse
)
import src.services.alert_service as alerts
from src.services.alert_service import AlertAlreadyReachedError
from src.services.auth_service import get_current_user_id


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.post(
    '/',
    response_model=AlertResponse,
    status_code=201,
    summary='Cadastra o valor de cotação que dispara a notificação'
)
async def create(
    alert: AlertCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    try:
        return await alerts.create_alert(db, user_id, alert)

    except AlertAlreadyReachedError as error:
        raise HTTPException(
            409,
            detail=str(error)
        )

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


@router.get('/', response_model=list[AlertResponse])
async def read_all(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    return await alerts.list_alerts(db, user_id)


@router.delete('/{alert_id}', status_code=204)
async def delete(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    success = await alerts.delete_alert(db, user_id, alert_id)

    if not success:
        raise HTTPException(
            404,
            detail='Alert not found'
        )


@router.get(
    '/messages',
    response_model=list[MessageResponse],
    summary='Histórico de notificações disparadas'
)
async def read_messages(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    return await alerts.list_messages(db, user_id)
