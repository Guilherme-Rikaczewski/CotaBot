from sqlalchemy import Column, Integer, String, DateTime, func, Text
from src.db.base import Base


class Coins(Base):
    __tablename__ = "coins"

    id = Column(Integer, primary_key=True)

    coin_name = Column(Text, nullable=False)

    value = Column(Text, nullable=False)

    request_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
