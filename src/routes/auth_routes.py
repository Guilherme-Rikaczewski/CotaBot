from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Cookie
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.auth_schema import TokenData
from datetime import timedelta
from src.utils.refresh import create_opaque_token
from src.cache.redis_client import connection
import src.services.auth_service as aus
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

ACCESS_TOKEN_EXPIRE_MINUTES = 15


@router.post('/login/')
async def login(
    response: Response,
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends()
    ],
    db: AsyncSession = Depends(get_db)
):

    try:

        authenticated_user = await aus.authenticate_user(
            db,
            form_data.username,
            form_data.password
        )

        if not authenticated_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        token_data = TokenData(
            id=authenticated_user.id
        )

        access_token_expires = timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

        access_token = aus.create_access_token(
            {'id': token_data.id},
            access_token_expires
        )

        refresh_token = create_opaque_token()

        await aus.save_refresh_token(
            token_data.id,
            refresh_token,
            connection
        )

        response.set_cookie(
            key='accessToken',
            value=access_token,
            httponly=True,
            secure=False,
            samesite='strict',
            path="/",
            max_age=60 * 60
        )

        response.set_cookie(
            key='refreshToken',
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite='strict',
            path="/",
            max_age=60 * 60 * 24 * 7
        )

        return {
            "message": "Login successful"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            500,
            detail=f'Internal server error: {error}'
        )


@router.post('/refresh/')
async def new_refresh(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias="refreshToken"
    )
):

    try:

        if not refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        user_id = await aus.consume_refresh_token(
            refresh_token,
            connection
        )

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        new_refresh_token = create_opaque_token()

        await aus.save_refresh_token(
            user_id,
            new_refresh_token,
            connection
        )

        token_data = TokenData(id=user_id)

        access_token_expires = timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

        access_token = aus.create_access_token(
            {'id': token_data.id},
            access_token_expires
        )

        response.set_cookie(
            key='accessToken',
            value=access_token,
            httponly=True,
            secure=False,
            samesite='strict',
            path="/",
            max_age=60 * 60
        )

        response.set_cookie(
            key='refreshToken',
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite='strict',
            path="/",
            max_age=60 * 60 * 24 * 7
        )

        return {
            'message': 'Refresh successful'
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            500,
            detail='Internal server error'
        )


@router.post('/logout/')
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias="refreshToken"
    )
):

    try:

        if refresh_token:

            user_id = await aus.validate_refresh_token(
                refresh_token,
                connection
            )

            if user_id:
                await aus.delete_refresh_token(
                    refresh_token,
                    connection
                )

        response.delete_cookie(
            key="refreshToken",
            path="/"
        )

        response.delete_cookie(
            key="accessToken",
            path="/"
        )

        return {
            'message': 'Logout successful'
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            500,
            detail='Internal server error'
        )
