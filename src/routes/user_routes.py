from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse
)
import src.services.user_service as us
from src.services.auth_service import get_current_user_id


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/", response_model=UserResponse)
async def create(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):

    try:
        return await us.create_user(db, user)

    except Exception as error:
        raise HTTPException(
            500,
            detail=f'Internal server error {error}'
        )


@router.patch('/', response_model=UserResponse)
async def update(
    user: UserUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    try:
        updated_user = await us.update_user(
            db,
            user_id,
            user
        )

        if not updated_user:
            raise HTTPException(
                404,
                detail='User not found'
            )

        return updated_user

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            500,
            detail='Internal server error'
        )


@router.get('/', response_model=UserResponse)
async def read(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    try:
        user = await us.get_user(db, user_id)

        if not user:
            raise HTTPException(
                404,
                detail='User not found'
            )

        return user

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            500,
            detail='Internal server error'
        )


@router.delete('/', status_code=204)
async def delete(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    try:
        success = await us.delete_user(
            db,
            user_id
        )

        if not success:
            raise HTTPException(
                404,
                detail='User not found'
            )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            500,
            detail='Internal server error'
        )
