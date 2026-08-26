from datetime import datetime
from pydantic import BaseModel


class CoinToCoinResponse(BaseModel):
    conversion: float

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
