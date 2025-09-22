# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Обновляем pip
RUN pip install --no-cache-dir --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . /app

# Открываем порт
EXPOSE ${PORT}

# Команда запуска
CMD ["python", "-m", "server"]
