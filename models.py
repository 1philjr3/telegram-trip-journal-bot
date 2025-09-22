from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import uuid


class Registration(BaseModel):
    """Модель регистрации пользователя"""
    telegram_user_id: int
    full_name: str
    created_at: str


class TripEntry(BaseModel):
    """Модель записи поездки"""
    date: str
    time_start: str  # ЧЧ:ММ
    time_end: str    # ЧЧ:ММ
    odometer_start: int
    odometer_end: int
    distance_km: int
    engineer: str
    project: Optional[str] = ""
    address: Optional[str] = ""
    comment: str = ""
    created_at: str
    author_tg_id: int
    row_uid: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @validator('odometer_end')
    def validate_odometer_end(cls, v, values):
        if 'odometer_start' in values and v < values['odometer_start']:
            raise ValueError('Конечный одометр должен быть больше или равен начальному')
        return v

    @validator('distance_km', always=True)
    def calculate_distance(cls, v, values):
        if 'odometer_start' in values and 'odometer_end' in values:
            return values['odometer_end'] - values['odometer_start']
        return v

    def to_sheets_row(self) -> list:
        """Преобразует запись в массив для Google Sheets"""
        return [
            self.date,
            self.time_start,
            self.time_end,
            str(self.odometer_start),
            str(self.odometer_end),
            str(self.distance_km),
            self.engineer,
            self.project or "",
            self.address or "",
            self.comment,
            self.created_at,
            str(self.author_tg_id),
            self.row_uid
        ]

    @classmethod
    def get_headers(cls) -> list:
        """Возвращает заголовки для Google Sheets"""
        return [
            "date",
            "time_start", 
            "time_end",
            "odometer_start",
            "odometer_end",
            "distance_km",
            "engineer",
            "project",
            "address",
            "comment",
            "created_at",
            "author_tg_id",
            "row_uid"
        ]
