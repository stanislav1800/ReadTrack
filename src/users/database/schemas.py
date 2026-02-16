from datetime import datetime
from typing import Optional

import pytz
from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    created_at: datetime

    def __str__(self):
        return (
            "<Users"
            + (f" telegram_id={self.telegram_id}" if self.telegram_id else "")
            + (f" username='{self.username}'" if self.username else "")
            + (f" first_name='{self.first_name}'" if self.first_name else "")
            + (f" last_name='{self.last_name}'" if self.last_name else "")
            + (f" is_active={self.is_active}")
            + (f" is_superuser={self.is_superuser}")
            + (f" is_verified={self.is_verified}")
            + ">"
        )

    def format_datetime(self) -> str:
        tz = pytz.timezone("Asia/Novosibirsk")
        dt = self.created_at.astimezone(tz)
        return dt.strftime("%d.%m.%Y %H:%M")
