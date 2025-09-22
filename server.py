#!/usr/bin/env python3
"""
HTTP-сервер для Telegram webhook
Импортирует ВСЮ логику из оригинального bot.py
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
app_logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(title="Telegram Bot Webhook", version="1.0.0")

from bot import bot as bot_instance, dp as dp_instance, sheets_client as sheets_client_instance

# Глобальные переменные
bot_initialized = True
dp = dp_instance
bot = bot_instance


async def initialize_bot():
    return


async def handle_telegram_update(update_dict: Dict[str, Any]) -> None:
    """Обрабатывает обновление от Telegram"""
    try:
        app_logger.info(f"Получено обновление: {update_dict.get('update_id', 'unknown')}")
        
        # Инициализация уже сделана через импорт
        
        if dp is None or bot is None:
            app_logger.error("Бот не инициализирован")
            return
        
        from aiogram.types import Update
        update = Update.model_validate(update_dict)
        
        await dp.feed_update(bot, update)
        
        app_logger.info(f"Обработано обновление: {update_dict.get('update_id', 'unknown')}")
        
    except Exception as e:
        app_logger.error(f"Ошибка при обработке обновления: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global bot_initialized
    if not bot_initialized:
        app_logger.info("Инициализация Telegram бота...")
        try:
            await initialize_bot()
            app_logger.info("Telegram бот готов к работе")
        except Exception as e:
            app_logger.error(f"Ошибка инициализации бота: {e}")


@app.post("/")
async def webhook_handler(request: Request):
    """Обработчик webhook от Telegram"""
    try:
        update_data = await request.json()
        app_logger.info(f"Получено обновление: {update_data.get('update_id', 'unknown')}")
        
        # Обработка в фоне, чтобы отвечать Telegram мгновенно
        asyncio.create_task(handle_telegram_update(update_data))
        return JSONResponse(content={"ok": True})
        
    except json.JSONDecodeError:
        app_logger.error("Ошибка парсинга JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    except Exception as e:
        app_logger.error(f"Ошибка обработки webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return JSONResponse(content={"status": "healthy", "bot_initialized": bot_initialized})


@app.get("/")
async def root():
    """Корневой endpoint"""
    return JSONResponse(content={
        "message": "Telegram Bot Webhook Server",
        "status": "running",
        "bot_initialized": bot_initialized
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app_logger.info(f"Запуск сервера на порту {port}")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )