# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Устанавливаем системные зависимости для OpenCV и других библиотек
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    TORCH_HOME=/tmp/.torch \
    YOLO_VERBOSE=False

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
