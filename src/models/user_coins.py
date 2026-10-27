from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey
from src.db.base import Base


class UserCoins(Base):
    __tablename__ = "user_coins"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    email_by_bot = Column(String(256), index=True)

    coin_name = Column(String(50), nullable=False)

    target_value_expected = Column(String(30), nullable=False)

    expect = Column(String(4), nullable=False)

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
