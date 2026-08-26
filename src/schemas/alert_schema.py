from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints


CoinName = Annotated[
    str,
    StringConstraints(
        max_length=50,
        min_length=1,
        strip_whitespace=True,
        to_upper=True
    )
]


class AlertCreate(BaseModel):
    """Alerta de cotação escolhido pelo usuário."""

    coin_name: CoinName
    target_value_expected: float = Field(gt=0)


class AlertResponse(BaseModel):
    id: int
    coin_name: str
    target_value_expected: float
    notified_at: datetime | None
    created_at: datetime

    model_config = {'from_attributes': True}


class MessageResponse(BaseModel):
    id: int
    message: str
    created_at: datetime

    model_config = {'from_attributes': True}
