from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.user_schema import (
    UserCreate,
    UserUpdate
)
from src.models.users import User
from src.utils.hasher import get_password_hash
from sqlalchemy import select


async def create_user(
    db: AsyncSession,
    user_data: UserCreate
) -> User:

    user = User(**user_data.model_dump())

    user.password = get_password_hash(user.password)

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    user_data: UserUpdate
) -> User | None:

    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            return None

        update_data = user_data.model_dump(
            exclude_unset=True,
            exclude_none=True
        )

        if 'password' in update_data:
            update_data['password'] = get_password_hash(
                update_data['password']
            )

        for k, v in update_data.items():

            if isinstance(v, str):
                v = v.strip()

            setattr(user, k, v)

        await db.commit()
        await db.refresh(user)

        return user

    except Exception:
        await db.rollback()
        raise


async def get_user(
    db: AsyncSession,
    user_id: int
) -> User | None:

    try:
        user = await db.get(User, user_id)

        if not user:
            return None

        return user

    except Exception:
        raise


async def delete_user(
    db: AsyncSession,
    user_id: int
) -> bool:

    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            return False

        await db.delete(user)
        await db.commit()

        return True

    except Exception:
        await db.rollback()
        raise
