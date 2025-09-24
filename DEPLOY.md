# 🚀 Деплой через GitHub Actions в Yandex Cloud

Этот проект настроен для автоматического деплоя в Yandex Cloud Serverless Containers через GitHub Actions.

## 🔧 Настройка GitHub Secrets

Перейдите в ваш репозиторий GitHub → Settings → Secrets and variables → Actions → New repository secret

Добавьте следующие секреты:

### Yandex Cloud настройки:

1. **YC_SA_KEY** - JSON-ключ сервисного аккаунта:
   ```bash
   # Создайте сервисный аккаунт с правами:
   # - serverless.containers.invoker
   # - container-registry.images.puller  
   # - container-registry.images.pusher
   # - ydb.admin
   
   yc iam service-account create --name github-actions-sa
   yc resource-manager folder add-access-binding <FOLDER_ID> \
     --role serverless.containers.invoker \
     --subject serviceAccount:<SERVICE_ACCOUNT_ID>
   
   # Создайте JSON-ключ и вставьте весь содержимый файла в секрет
   yc iam key create --service-account-name github-actions-sa --output sa-key.json
   ```

2. **YC_CLOUD_ID** - ID вашего облака
   ```bash
   yc config list  # найдите cloud-id
   ```

3. **YC_FOLDER_ID** - ID папки
   ```bash
   yc config list  # найдите folder-id
   ```

4. **YC_REGISTRY_ID** - ID Container Registry
   ```bash
   yc container registry list
   ```

5. **YC_SERVICE_ACCOUNT_ID** - ID сервисного аккаунта для контейнера
   ```bash
   yc iam service-account list
   ```

### Telegram и Google настройки:

6. **TELEGRAM_BOT_TOKEN** - токен вашего Telegram бота
7. **GOOGLE_SHEET_ID** - ID Google Sheets таблицы
8. **GOOGLE_SHEET_NAME** - название листа (обычно "Лист1")
9. **ADMIN_IDS** - ID админов через запятую (например: "123456789,987654321")

## 🏗️ Подготовка инфраструктуры

### 1. Создание Serverless Container:
```bash
yc serverless container create --name telegram-bot-trips
yc serverless container allow-unauthenticated-invoke --name telegram-bot-trips
```

### 2. Создание API Gateway:

Создайте файл `api-gw.yaml`:
```yaml
openapi: 3.0.0
info:
  title: tg-bot-gw
  version: 1.0.0
  description: API Gateway для Telegram бота
paths:
  /:
    post:
      summary: Telegram webhook endpoint
      x-yc-apigateway-integration:
        type: serverless_containers
        container_id: <ВАША_CONTAINER_ID>
        service_account_id: <ВАШ_SERVICE_ACCOUNT_ID>
      responses:
        '200':
          description: OK
  /health:
    get:
      summary: Health check
      x-yc-apigateway-integration:
        type: serverless_containers
        container_id: <ВАША_CONTAINER_ID>
        service_account_id: <ВАШ_SERVICE_ACCOUNT_ID>
      responses:
        '200':
          description: OK
```

```bash
yc serverless api-gateway create --name telegram-bot-trips --spec api-gw.yaml
```

### 3. Добавление модели YOLO:

Поместите ваш файл `best.pt` в корень репозитория.

## 🚀 Деплой

После настройки секретов деплой происходит автоматически:

1. **При push в main ветку** - запускается полный деплой
2. **При создании Pull Request** - запускается только проверка сборки

### Процесс деплоя:

1. ✅ Checkout кода
2. ✅ Настройка Docker Buildx  
3. ✅ Установка Yandex Cloud CLI
4. ✅ Авторизация в Yandex Cloud
5. ✅ Сборка и push Docker образа
6. ✅ Деплой новой ревизии Serverless Container
7. ✅ Обновление webhook в Telegram

## 📊 Мониторинг

### Просмотр логов:
```bash
# Логи последнего часа
yc logging read --folder-id <FOLDER_ID> --resource-types serverless-container --since 1h

# Логи конкретного контейнера
yc serverless container revision list --container-name telegram-bot-trips
```

### Проверка webhook:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

### Health check:
```bash
curl "https://<APIGW_DOMAIN>/health"
```

## 🔄 Обновления

Для обновления бота просто сделайте commit и push в main ветку:

```bash
git add .
git commit -m "Добавлена новая функция"
git push origin main
```

GitHub Actions автоматически:
- Соберет новый образ с обновлениями
- Задеплоит его в Yandex Cloud
- Обновит webhook

## 🐛 Отладка

### Если деплой упал:

1. Проверьте логи GitHub Actions во вкладке "Actions"
2. Убедитесь, что все секреты настроены правильно
3. Проверьте права сервисного аккаунта

### Частые проблемы:

- **"Permission denied"** - проверьте права сервисного аккаунта
- **"Container not found"** - убедитесь, что контейнер создан
- **"Registry not found"** - проверьте YC_REGISTRY_ID
- **"Image too large"** - образ с YOLOv8 может быть большим, увеличьте timeout

## 💰 Стоимость

При использовании GitHub Actions + Yandex Cloud Serverless:

- **GitHub Actions**: 2000 бесплатных минут в месяц
- **Serverless Containers**: первый 1 млн вызовов бесплатно
- **API Gateway**: первые 100к вызовов бесплатно  
- **Container Registry**: ~10-20₽ в месяц за хранение образов

Итого: практически бесплатно для небольших ботов! 🎉
