from sqlalchemy import Column, Integer, DateTime, func, String
from src.db.base import Base


class Coins(Base):
    __tablename__ = "coins"

    id = Column(Integer, primary_key=True)

    coin_name_origin = Column(String(50), nullable=False)

    coin_name_target = Column(String(50), nullable=False)

    coin_origin_value = Column(String(30), nullable=False)

    coin_target_value = Column(String(30), nullable=False)

    request_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
