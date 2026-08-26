from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Quote(BaseModel):
    """Cotação de um par de moedas retornada pela AwesomeAPI.

    Os campos descritivos (`code`, `codein`, `name`) e `create_date`
    são opcionais porque o endpoint de histórico só os envia no
    primeiro item da lista.
    """

    code: str | None = None
    codein: str | None = None
    name: str | None = None
    high: float
    low: float
    var_bid: float = Field(alias='varBid')
    pct_change: float = Field(alias='pctChange')
    bid: float
    ask: float
    timestamp: datetime
    create_date: datetime | None = None

    model_config = {
        'from_attributes': True,
        'populate_by_name': True
    }

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, value):
        if isinstance(value, (str, int, float)):
            return datetime.fromtimestamp(int(value))

        return value

    @property
    def pair(self) -> str | None:
        if not self.code or not self.codein:
            return None

        return f'{self.code}-{self.codein}'
