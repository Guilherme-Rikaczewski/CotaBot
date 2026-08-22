from typing import Annotated
from pydantic import (
    AfterValidator,
    StringConstraints
)
from pydantic import BaseModel, EmailStr
from datetime import datetime


def validate_password(password: str) -> str:
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain a lowercase letter")

    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain an uppercase letter")

    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain a number")

    return password


Username = Annotated[
    str,
    StringConstraints(
        max_length=50,
        min_length=1,
        strip_whitespace=True,
    )
]

Password = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=50,
        strip_whitespace=True,
    ),
    AfterValidator(validate_password)
]


class UserCreate(BaseModel):
    email: EmailStr
    username: Username
    password: Password


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: Username | None = None
    password: Password | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: Username
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
