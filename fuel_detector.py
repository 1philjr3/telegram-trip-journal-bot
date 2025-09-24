#!/usr/bin/env python3
"""
Модуль для детекции уровня топлива с помощью YOLOv8
"""

import logging
import os
import io
from typing import Optional, Tuple
from PIL import Image
import cv2
import numpy as np

# Импорт YOLO будет выполнен при первом использовании
# для избежания ошибок при отсутствии зависимостей

logger = logging.getLogger(__name__)


class FuelDetector:
    """Класс для детекции уровня топлива с помощью YOLOv8"""
    
    def __init__(self, model_path: str = "./best.pt"):
        """
        Инициализация детектора
        
        Args:
            model_path: Путь к модели YOLO
        """
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Загружает модель YOLO"""
        try:
            from ultralytics import YOLO
            
            if not os.path.exists(self.model_path):
                logger.error(f"Модель не найдена: {self.model_path}")
                return
            
            self.model = YOLO(self.model_path)
            logger.info(f"Модель YOLO загружена: {self.model_path}")
            
        except ImportError:
            logger.error("Не удалось импортировать ultralytics. Установите: pip install ultralytics")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
    
    def detect_fuel_level(self, image_data: bytes) -> Tuple[Optional[int], Optional[float], str]:
        """
        Детекция уровня топлива на изображении
        
        Args:
            image_data: Байты изображения
            
        Returns:
            Tuple[bars_count, fuel_liters, status_message]
        """
        if not self.model:
            return None, None, "❌ Модель не загружена"
        
        try:
            # Конвертируем байты в PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Конвертируем в RGB если необходимо
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Запускаем детекцию
            results = self.model(image)
            
            if not results or len(results) == 0:
                return 0, 0.0, "❌ Не удалось обработать изображение"
            
            # Получаем результат первого изображения
            result = results[0]
            
            # Считаем количество найденных объектов класса active_bar
            bars_count = len(result.boxes) if result.boxes is not None else 0
            
            # Вычисляем количество топлива (1 палочка = 6.25 литров)
            fuel_liters = bars_count * 6.25
            
            if bars_count == 0:
                status = "❌ Палочки уровня топлива не найдены на фото"
            else:
                status = f"✅ Найдено {bars_count} палочек уровня топлива"
            
            logger.info(f"Детекция завершена: {bars_count} палочек, {fuel_liters} литров")
            
            return bars_count, fuel_liters, status
            
        except Exception as e:
            logger.error(f"Ошибка при детекции: {e}")
            return None, None, f"❌ Ошибка обработки изображения: {str(e)}"
    
    def is_available(self) -> bool:
        """Проверяет доступность детектора"""
        return self.model is not None


# Глобальный экземпляр детектора
fuel_detector = FuelDetector()

