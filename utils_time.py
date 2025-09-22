import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
import logging


logger = logging.getLogger(__name__)


class TimeUtils:
    """Утилиты для работы со временем"""
    
    def __init__(self, timezone: str = "Europe/Moscow"):
        self.timezone = pytz.timezone(timezone)
        self.utc = pytz.UTC

    def get_current_datetime(self) -> datetime:
        """Получает текущее время в локальной временной зоне"""
        return datetime.now(self.timezone)

    def get_current_utc_datetime(self) -> datetime:
        """Получает текущее время в UTC"""
        return datetime.now(self.utc)

    def parse_datetime_input(self, user_input: str) -> Optional[datetime]:
        """
        Парсит ввод пользователя для даты и времени
        Поддерживает форматы:
        - "сейчас" / "now"
        - "ДД.ММ.ГГГГ ЧЧ:ММ"
        - "ЧЧ:ММ" (сегодняшняя дата)
        """
        user_input = user_input.strip().lower()
        
        # Проверяем "сейчас"
        if user_input in ["сейчас", "now"]:
            return self.get_current_datetime()
        
        # Попытка парсинга полной даты и времени: ДД.ММ.ГГГГ ЧЧ:ММ
        full_datetime_pattern = r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})$'
        match = re.match(full_datetime_pattern, user_input)
        if match:
            day, month, year, hour, minute = map(int, match.groups())
            try:
                dt = datetime(year, month, day, hour, minute)
                return self.timezone.localize(dt)
            except ValueError as e:
                logger.error(f"Ошибка парсинга даты: {e}")
                return None
        
        # Попытка парсинга только времени: ЧЧ:ММ (используем сегодняшнюю дату)
        time_only_pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(time_only_pattern, user_input)
        if match:
            hour, minute = map(int, match.groups())
            try:
                today = self.get_current_datetime().date()
                dt = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                return self.timezone.localize(dt)
            except ValueError as e:
                logger.error(f"Ошибка парсинга времени: {e}")
                return None
        
        return None

    def format_datetime_for_sheets(self, dt: datetime) -> Tuple[str, str]:
        """
        Форматирует datetime для Google Sheets
        Возвращает кортеж (дата, время)
        """
        # Преобразуем в локальную временную зону, если нужно
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        elif dt.tzinfo != self.timezone:
            dt = dt.astimezone(self.timezone)
        
        date_str = dt.strftime("%d.%m.%Y")
        time_str = dt.strftime("%H:%M")
        
        return date_str, time_str

    def format_datetime_for_display(self, dt: datetime) -> str:
        """Форматирует datetime для отображения пользователю"""
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        elif dt.tzinfo != self.timezone:
            dt = dt.astimezone(self.timezone)
        
        return dt.strftime("%d.%m.%Y %H:%M")

    def get_utc_iso_string(self, dt: Optional[datetime] = None) -> str:
        """Получает ISO строку в UTC (для created_at)"""
        if dt is None:
            dt = self.get_current_utc_datetime()
        elif dt.tzinfo is None:
            dt = self.timezone.localize(dt).astimezone(self.utc)
        elif dt.tzinfo != self.utc:
            dt = dt.astimezone(self.utc)
        
        return dt.isoformat() + "Z"

    def parse_sheets_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Парсит дату и время из Google Sheets"""
        try:
            # Парсим дату в формате ДД.ММ.ГГГГ
            date_parts = date_str.split('.')
            if len(date_parts) != 3:
                return None
            
            day, month, year = map(int, date_parts)
            
            # Парсим время в формате ЧЧ:ММ
            time_parts = time_str.split(':')
            if len(time_parts) != 2:
                return None
            
            hour, minute = map(int, time_parts)
            
            dt = datetime(year, month, day, hour, minute)
            return self.timezone.localize(dt)
            
        except ValueError as e:
            logger.error(f"Ошибка парсинга даты/времени из Sheets: {e}")
            return None

    def is_within_edit_time_limit(self, created_at_str: str, limit_minutes: int = 15) -> bool:
        """Проверяет, можно ли еще редактировать запись (в пределах лимита времени)"""
        try:
            # Парсим ISO строку
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            current_time = self.get_current_utc_datetime()
            
            time_diff = current_time - created_at
            return time_diff.total_seconds() <= limit_minutes * 60
            
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при проверке времени редактирования: {e}")
            return False

    def validate_time_sequence(self, start_dt: datetime, end_dt: datetime) -> bool:
        """Проверяет, что время окончания больше времени начала"""
        return end_dt >= start_dt

    def format_duration(self, start_dt: datetime, end_dt: datetime) -> str:
        """Форматирует продолжительность между двумя временными точками"""
        duration = end_dt - start_dt
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
