from pydantic import BaseModel


class CoinToCoinResponse(BaseModel):
    conversion: float

    model_config = {'from_attributes': True}
