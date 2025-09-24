#!/usr/bin/env python3
"""
HTTP-сервер для Telegram webhook
Ленивая инициализация бота при первом входящем обновлении
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional
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

# Ленивая инициализация бота/диспетчера
bot_initialized: bool = False
bot = None  # type: ignore
dp = None   # type: ignore


async def initialize_bot_if_needed() -> None:
    global bot_initialized, bot, dp
    if bot_initialized and bot is not None and dp is not None:
        return
    try:
        app_logger.info("Инициализация Telegram бота (лениво)...")
        # Импортируем только при необходимости, чтобы избежать тяжёлых импорта на старте
        from bot import bot as bot_instance, dp as dp_instance
        bot = bot_instance
        dp = dp_instance
        bot_initialized = True
        app_logger.info("Telegram бот готов к работе")
    except Exception as e:
        app_logger.error(f"Ошибка инициализации бота: {e}")
        raise


async def handle_telegram_update(update_dict: Dict[str, Any]) -> None:
    """Обрабатывает обновление от Telegram"""
    await initialize_bot_if_needed()

    if dp is None or bot is None:
        app_logger.error("Бот не инициализирован")
        return

    from aiogram.types import Update
    update = Update.model_validate(update_dict)

    await dp.feed_update(bot, update)


@app.on_event("startup")
async def startup_event():
    # Ничего не делаем: инициализация ленивая
    return


@app.post("/")
async def webhook_handler(request: Request):
    """Обработчик webhook от Telegram"""
    try:
        update_data = await request.json()
        # Синхронная обработка вместо фоновой задачи — важна для serverless окружения
        await handle_telegram_update(update_data)
        return JSONResponse(content={"ok": True})
    except json.JSONDecodeError:
        app_logger.error("Ошибка парсинга JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        app_logger.error(f"Ошибка обработки webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy", "bot_initialized": bot_initialized})


@app.get("/")
async def root():
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