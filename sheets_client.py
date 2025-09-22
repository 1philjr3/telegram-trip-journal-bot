import os
import logging
from typing import List, Dict, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import TripEntry


logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Клиент для работы с Google Sheets"""
    
    def __init__(self, service_account_path: str, sheet_id: str, sheet_name: str = "Лист1"):
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        
        # Инициализация клиента Google Sheets
        # Проверяем, есть ли JSON в переменной окружения (для Render)
        google_sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if google_sa_json:
            import json
            from google.oauth2 import service_account as sa
            credentials_info = json.loads(google_sa_json)
            credentials = sa.Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
        else:
            # Локальный файл
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
        self.service = build("sheets", "v4", credentials=credentials)
        
        # Убеждаемся, что заголовки существуют
        self.ensure_header()

    def ensure_header(self) -> None:
        """Проверяет и создает заголовки, если лист пуст"""
        try:
            # Читаем первую строку
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A1:M1"
            ).execute()
            
            values = result.get('values', [])
            
            # Если лист пуст или первая строка не содержит заголовки
            if not values or values[0] != TripEntry.get_headers():
                logger.info("Создаем заголовки в Google Sheets")
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self.sheet_name}!A1:M1",
                    valueInputOption="RAW",
                    body={"values": [TripEntry.get_headers()]}
                ).execute()
                
        except HttpError as e:
            logger.error(f"Ошибка при работе с заголовками: {e}")
            raise

    def append_row(self, trip_entry: TripEntry) -> bool:
        """Добавляет новую строку в таблицу"""
        try:
            # Проверяем дубли в последние 30 секунд
            if self._check_duplicate(trip_entry):
                logger.warning(f"Дублирующая запись для пользователя {trip_entry.author_tg_id}")
                return False
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [trip_entry.to_sheets_row()]}
            ).execute()
            
            logger.info(f"Добавлена новая строка: {result.get('updates', {}).get('updatedRows', 0)}")
            return True
            
        except HttpError as e:
            logger.error(f"Ошибка при добавлении строки: {e}")
            return False

    def get_last_rows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает последние N строк из таблицы"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A:M"
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # Только заголовки или пусто
                return []
            
            headers = TripEntry.get_headers()
            rows = values[1:]  # Пропускаем заголовки
            
            # Берем последние N строк
            last_rows = rows[-limit:] if len(rows) > limit else rows
            
            # Преобразуем в словари
            result_rows = []
            for row in reversed(last_rows):  # Последние записи сначала
                if len(row) >= len(headers):
                    row_dict = dict(zip(headers, row))
                    result_rows.append(row_dict)
            
            return result_rows
            
        except HttpError as e:
            logger.error(f"Ошибка при чтении строк: {e}")
            return []

    def find_row_by_uid(self, row_uid: str, author_tg_id: int) -> Optional[tuple]:
        """Находит строку по row_uid и проверяет автора"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A:M"
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return None
            
            # Ищем строку с нужным row_uid
            for i, row in enumerate(values[1:], start=2):  # Начинаем с строки 2 (после заголовков)
                if len(row) >= 13 and row[12] == row_uid and row[11] == str(author_tg_id):
                    return (i, row)  # Возвращаем номер строки и данные
            
            return None
            
        except HttpError as e:
            logger.error(f"Ошибка при поиске строки: {e}")
            return None

    def update_row(self, row_number: int, trip_entry: TripEntry) -> bool:
        """Обновляет существующую строку"""
        try:
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A{row_number}:M{row_number}",
                valueInputOption="RAW",
                body={"values": [trip_entry.to_sheets_row()]}
            ).execute()
            
            logger.info(f"Обновлена строка {row_number}")
            return True
            
        except HttpError as e:
            logger.error(f"Ошибка при обновлении строки: {e}")
            return False

    def get_last_user_entry(self, author_tg_id: int) -> Optional[Dict[str, Any]]:
        """Получает последнюю запись пользователя"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A:M"
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return None
            
            headers = TripEntry.get_headers()
            
            # Ищем последнюю запись пользователя
            for row in reversed(values[1:]):
                if len(row) >= 12 and row[11] == str(author_tg_id):
                    row_dict = dict(zip(headers, row))
                    return row_dict
            
            return None
            
        except HttpError as e:
            logger.error(f"Ошибка при поиске последней записи пользователя: {e}")
            return None

    def _check_duplicate(self, trip_entry: TripEntry) -> bool:
        """Проверяет дубли в последние 30 секунд"""
        from datetime import datetime, timedelta
        
        try:
            # Получаем последние 10 записей
            last_rows = self.get_last_rows(10)
            
            # Время создания новой записи
            new_created_at = datetime.fromisoformat(trip_entry.created_at.replace('Z', '+00:00'))
            
            for row in last_rows:
                # Проверяем того же пользователя
                if int(row.get('author_tg_id', 0)) == trip_entry.author_tg_id:
                    # Проверяем время (в пределах 30 секунд)
                    try:
                        row_created_at = datetime.fromisoformat(row.get('created_at', '').replace('Z', '+00:00'))
                        time_diff = abs((new_created_at - row_created_at).total_seconds())
                        
                        if time_diff < 30:  # 30 секунд
                            return True
                            
                    except (ValueError, TypeError):
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке дублей: {e}")
            return False
