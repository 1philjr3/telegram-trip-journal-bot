#!/usr/bin/env python3
"""
Модуль для детекции уровня топлива с помощью YOLOv8 (ленивая загрузка модели)
"""

import logging
import os
import io
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class FuelDetector:
    """Класс для детекции уровня топлива с помощью YOLOv8"""

    def __init__(self, model_path: str = "./best.pt"):
        self.model_path = model_path
        self.model = None  # Ленивая загрузка

    def _load_model(self) -> bool:
        """Загружает модель YOLO по требованию."""
        if self.model is not None:
            return True
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Модель не найдена: {self.model_path}")
                return False
            from ultralytics import YOLO  # импортируем только при необходимости
            self.model = YOLO(self.model_path)
            logger.info(f"Модель YOLO загружена: {self.model_path}")
            return True
        except ImportError:
            logger.error("Не удалось импортировать ultralytics. Установите зависимость: pip install ultralytics")
            return False
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            return False

    def detect_fuel_level(self, image_data: bytes) -> Tuple[Optional[int], Optional[float], str]:
        """Детекция уровня топлива на изображении."""
        # Ленивая загрузка модели
        if self.model is None and not self._load_model():
            return None, None, "❌ Модель не загружена (проверьте зависимости и файл best.pt)"
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            results = self.model(image)
            if not results or len(results) == 0:
                return 0, 0.0, "❌ Не удалось обработать изображение"
            result = results[0]
            bars_count = len(result.boxes) if getattr(result, 'boxes', None) is not None else 0
            fuel_liters = bars_count * 6.25
            status = (
                f"✅ Найдено {bars_count} палочек уровня топлива" if bars_count > 0
                else "❌ Палочки уровня топлива не найдены на фото"
            )
            logger.info(f"Детекция завершена: {bars_count} палочек, {fuel_liters} литров")
            return bars_count, fuel_liters, status
        except Exception as e:
            logger.error(f"Ошибка при детекции: {e}")
            return None, None, f"❌ Ошибка обработки изображения: {str(e)}"

    def is_available(self) -> bool:
        return self.model is not None


# Глобальный экземпляр (лёгкий, модель загружается при первом использовании)
fuel_detector = FuelDetector()

