import os
import logging
from typing import Optional, Dict, List
from models import Registration
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


class UsersRepository:
    """Репозиторий пользователей в Google Sheets (лист "Пользователи")."""

    USERS_HEADERS: List[str] = [
        "telegram_user_id",
        "full_name",
        "created_at",
    ]

    def __init__(self, users_sheet_name: Optional[str] = None):
        self.users: Dict[int, Registration] = {}

        # Параметры доступа к Google Sheets
        self.sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "").strip()
        self.users_sheet_name: str = users_sheet_name or os.getenv("USERS_SHEET_NAME", "Пользователи")
        service_account_path: str = os.getenv("GOOGLE_SA_JSON_PATH", "./service_account.json")

        if not self.sheet_id:
            logger.error("GOOGLE_SHEET_ID не установлен – репозиторий пользователей работать не сможет")
            return

        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self.service = build("sheets", "v4", credentials=credentials)
        except Exception as e:
            logger.error(f"Не удалось инициализировать Google Sheets клиент для пользователей: {e}")
            self.service = None
            return

        # Готовим лист и локальный кэш
        self._ensure_users_header()
        self.load_users()

    def _ensure_users_header(self) -> None:
        if not getattr(self, "service", None):
            return
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.users_sheet_name}!A1:C1",
            ).execute()
            values = result.get("values", [])
            if not values or values[0] != self.USERS_HEADERS:
                logger.info("Создаем заголовки листа Пользователи")
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self.users_sheet_name}!A1:C1",
                    valueInputOption="RAW",
                    body={"values": [self.USERS_HEADERS]},
                ).execute()
        except HttpError as e:
            logger.error(f"Ошибка при проверке/создании заголовков пользователей: {e}")

    def load_users(self) -> None:
        """Загружает пользователей из листа Google Sheets в память."""
        self.users = {}
        if not getattr(self, "service", None):
            return
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{self.users_sheet_name}!A:C",
            ).execute()
            values = result.get("values", [])
            if len(values) <= 1:
                logger.info("Лист Пользователи пуст")
                return
            headers = values[0]
            rows = values[1:]
            # Ожидаем порядок headers = USERS_HEADERS
            for row in rows:
                if len(row) < 3:
                    continue
                try:
                    user_id = int(row[0])
                except ValueError:
                    continue
                registration = Registration(
                    telegram_user_id=user_id,
                    full_name=row[1],
                    created_at=row[2],
                )
                self.users[user_id] = registration
            logger.info(f"Загружено {len(self.users)} пользователей из Google Sheets")
        except HttpError as e:
            logger.error(f"Ошибка при чтении пользователей из Google Sheets: {e}")

    def save_users(self) -> None:
        """Ничего не делает: запись происходит при регистрации (append). Оставлено для совместимости."""
        return

    def get_user(self, telegram_user_id: int) -> Optional[Registration]:
        return self.users.get(telegram_user_id)

    def is_registered(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.users

    def register_user(self, telegram_user_id: int, full_name: str) -> Registration:
        """Регистрирует пользователя и сохраняет строку в листе Google Sheets."""
        registration = Registration(
            telegram_user_id=telegram_user_id,
            full_name=full_name.strip(),
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        # Сначала обновим локальный кэш
        self.users[telegram_user_id] = registration

        # Затем добавим строку в лист
        if getattr(self, "service", None) and self.sheet_id:
            try:
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.sheet_id,
                    range=f"{self.users_sheet_name}!A1",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={
                        "values": [[
                            str(registration.telegram_user_id),
                            registration.full_name,
                            registration.created_at,
                        ]]
                    },
                ).execute()
            except HttpError as e:
                logger.error(f"Ошибка при сохранении пользователя в Google Sheets: {e}")

        logger.info(f"Зарегистрирован пользователь {full_name} (ID: {telegram_user_id})")
        return registration

    def get_user_name(self, telegram_user_id: int) -> Optional[str]:
        user = self.get_user(telegram_user_id)
        return user.full_name if user else None

    def get_all_users_count(self) -> int:
        return len(self.users)

    def get_user_list(self) -> list:
        return [
            {
                "id": user_id,
                "name": reg.full_name,
                "created_at": reg.created_at,
            }
            for user_id, reg in self.users.items()
        ]
