from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey
from src.db.base import Base


class UserCoins(Base):
    __tablename__ = "user_coins"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    coin_name = Column(String(50), nullable=False)

    target_value_expected = Column(String(30), nullable=False)

    # Preenchido quando o alvo é atingido; alertas já avisados não
    # disparam de novo.
    notified_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
