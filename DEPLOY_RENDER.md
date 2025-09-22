# Деплой на Render.com

## Подготовка

1. **Зарегистрируйтесь на [Render.com](https://render.com)**
2. **Подключите GitHub аккаунт** к Render

## Шаг 1: Подготовка service_account.json

Поскольку файлы не должны храниться в Git, нужно преобразовать содержимое `service_account.json` в переменную окружения:

```bash
# Скопируйте содержимое файла service_account.json
cat service_account.json
```

Скопируйте весь JSON (включая фигурные скобки) для использования в переменных окружения.

## Шаг 2: Создание сервиса в Render

1. **Войдите в Render Dashboard**
2. **Нажмите "New +"** → **"Web Service"**
3. **Подключите ваш GitHub репозиторий**: `https://github.com/1philjr3/telegram-trip-journal-bot`
4. **Настройки сервиса**:
   - **Name**: `telegram-trip-journal-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 bot.py`
   - **Plan**: `Free` (для тестирования)

## Шаг 3: Настройка переменных окружения

В разделе **Environment Variables** добавьте:

### Обязательные переменные:
```
TELEGRAM_BOT_TOKEN = ваш_токен_от_BotFather
GOOGLE_SHEET_ID = ваш_id_таблицы
ADMIN_IDS = ваш_telegram_id
```

### JSON сервисного аккаунта:
```
GOOGLE_SERVICE_ACCOUNT_JSON = {"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
```

### Дополнительные переменные:
```
GOOGLE_SA_JSON_PATH = ./service_account.json
GOOGLE_SHEET_NAME = Лист1
TIMEZONE = Europe/Moscow
```

## Шаг 4: Деплой

1. **Нажмите "Create Web Service"**
2. **Render автоматически**:
   - Склонирует репозиторий
   - Установит зависимости
   - Запустит бота

## Шаг 5: Проверка

1. **Проверьте логи** в Render Dashboard
2. **Протестируйте бота** в Telegram
3. **Убедитесь**, что записи сохраняются в Google Sheets

## Альтернативные способы деплоя

### Через Docker:
Render поддерживает Docker. Используйте файл `Dockerfile` из репозитория.

### Через render.yaml:
Можно использовать Infrastructure as Code с файлом `render.yaml`.

## Мониторинг

- **Логи**: Render Dashboard → Your Service → Logs
- **Метрики**: Render Dashboard → Your Service → Metrics
- **Статус**: Бот должен показывать статус "Running"

## Ограничения Free Plan

- **750 часов** в месяц
- **Автоматический сон** после 15 минут бездействия
- **Холодный старт** может занимать несколько секунд

## Troubleshooting

### Бот не отвечает:
1. Проверьте переменные окружения
2. Проверьте логи на ошибки
3. Убедитесь, что токен бота корректен

### Ошибки Google Sheets:
1. Проверьте `GOOGLE_SERVICE_ACCOUNT_JSON`
2. Убедитесь, что сервисный аккаунт имеет доступ к таблице
3. Проверьте `GOOGLE_SHEET_ID`

### Проблемы с деплоем:
1. Проверьте `requirements.txt`
2. Убедитесь, что команда запуска корректна
3. Проверьте логи сборки

## Обновление

Для обновления бота:
1. **Push изменения** в GitHub
2. **Render автоматически** пересоберет и перезапустит сервис

## Безопасность

- ✅ Секретные данные в переменных окружения
- ✅ Файлы с секретами исключены из Git
- ✅ Используется HTTPS для всех соединений
