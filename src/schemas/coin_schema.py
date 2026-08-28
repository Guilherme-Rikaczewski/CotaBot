from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class Interval(Enum):
    minute = 'minute'
    hour = 'hour'
    day = 'day'


class CoinToCoinResponse(BaseModel):
    conversion: float

    model_config = {'from_attributes': True}


class CointAtInterval(BaseModel):
    conversion_value: float
    created_at: datetime


class CoinToCoinPeriodResponse(BaseModel):
    conversions: list[CointAtInterval] = Field(default_factory=list)

    model_config = {'from_attributes': True}


class RealtimeQuoteResponse(BaseModel):
    """Cotação atual consultada diretamente na AwesomeAPI."""

    origin: str
    target: str
    conversion: float
    high: float
    low: float
    pct_change: float
    updated_at: datetime

    model_config = {'from_attributes': True}
