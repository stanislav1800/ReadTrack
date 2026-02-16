import logging
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from src.core.config import settings
from src.database.base import Base

logger = logging.getLogger(__name__)


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        unique=True,
        comment="Внешний ID пользователя (например, Telegram ID)",
    )
    username: Mapped[str] = mapped_column(
        String(256),
        nullable=True,
        comment="username пользователя",
    )
    first_name: Mapped[str] = mapped_column(
        String(256),
        nullable=True,
        comment="first_name пользователя",
    )
    last_name: Mapped[str] = mapped_column(
        String(256),
        nullable=True,
        comment="last_name пользователя",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        comment="Когда зарегистрировался",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Когда профиль в последний раз обновлялся",
    )

    def __str__(self):
        return (
            "<Users"
            + (f" telegram_id={self.telegram_id}" if self.telegram_id else "")
            + (f" username='{self.username}'" if self.username else "")
            + (f" first_name='{self.first_name}'" if self.first_name else "")
            + (f" last_name='{self.last_name}'" if self.last_name else "")
            + ">"
        )
