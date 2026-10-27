from sqlalchemy import Column, Integer, DateTime, func, Text, ForeignKey, String
from src.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    email_by_bot = Column(String(256), index=True)

    message = Column(Text, nullable=False, default='')

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
