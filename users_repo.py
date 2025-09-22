import json
import os
import logging
from typing import Optional, Dict
from models import Registration
from datetime import datetime


logger = logging.getLogger(__name__)


class UsersRepository:
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, users_file: str = "users.json"):
        self.users_file = users_file
        self.users: Dict[int, Registration] = {}
        self.load_users()

    def load_users(self) -> None:
        """Загружает пользователей из JSON файла"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for user_id_str, user_data in data.items():
                    user_id = int(user_id_str)
                    self.users[user_id] = Registration(**user_data)
                    
                logger.info(f"Загружено {len(self.users)} пользователей")
            else:
                logger.info("Файл пользователей не найден, создастся при первой регистрации")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке пользователей: {e}")
            self.users = {}

    def save_users(self) -> None:
        """Сохраняет пользователей в JSON файл"""
        try:
            # Преобразуем в dict для JSON
            data = {}
            for user_id, registration in self.users.items():
                data[str(user_id)] = registration.dict()
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Сохранено {len(self.users)} пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении пользователей: {e}")

    def get_user(self, telegram_user_id: int) -> Optional[Registration]:
        """Получает пользователя по Telegram ID"""
        return self.users.get(telegram_user_id)

    def is_registered(self, telegram_user_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        return telegram_user_id in self.users

    def register_user(self, telegram_user_id: int, full_name: str) -> Registration:
        """Регистрирует нового пользователя"""
        registration = Registration(
            telegram_user_id=telegram_user_id,
            full_name=full_name.strip(),
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
        self.users[telegram_user_id] = registration
        self.save_users()
        
        logger.info(f"Зарегистрирован пользователь {full_name} (ID: {telegram_user_id})")
        return registration

    def get_user_name(self, telegram_user_id: int) -> Optional[str]:
        """Получает имя пользователя по Telegram ID"""
        user = self.get_user(telegram_user_id)
        return user.full_name if user else None

    def get_all_users_count(self) -> int:
        """Возвращает количество зарегистрированных пользователей"""
        return len(self.users)

    def get_user_list(self) -> list:
        """Возвращает список всех пользователей (для админов)"""
        return [
            {
                "id": user_id,
                "name": reg.full_name,
                "created_at": reg.created_at
            }
            for user_id, reg in self.users.items()
        ]
