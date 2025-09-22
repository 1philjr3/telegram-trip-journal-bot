# Makefile для автоматизации деплоя Telegram бота в Yandex Cloud
# Загружаем переменные из .env
include .env

# Экспортируем PATH для yc
export PATH := $(HOME)/yandex-cloud/bin:$(PATH)

.PHONY: help create create_gw_spec create_gw webhook_info webhook_delete webhook_create build push deploy all clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

create: ## Создать Serverless Container
	@echo "Создание Serverless Container..."
	yc serverless container create --name $(SERVERLESS_CONTAINER_NAME) || true
	yc serverless container allow-unauthenticated-invoke --name $(SERVERLESS_CONTAINER_NAME) || true
	@echo "Container создан: $(SERVERLESS_CONTAINER_NAME)"

create_gw_spec: ## Создать спецификацию API Gateway
	@echo "Создание спецификации API Gateway..."
	@sed "s/SERVERLESS_CONTAINER_ID/${SERVERLESS_CONTAINER_ID}/;s/SERVICE_ACCOUNT_ID/${SERVICE_ACCOUNT_ID}/" api-gw.yaml.example > api-gw.yaml
	@echo "Спецификация создана: api-gw.yaml"

create_gw: create_gw_spec ## Создать API Gateway
	@echo "Создание API Gateway..."
	yc serverless api-gateway create --name $(SERVERLESS_CONTAINER_NAME) --spec api-gw.yaml || true
	@yc serverless api-gateway get --name $(SERVERLESS_CONTAINER_NAME) --format json | jq -r '.domain' | xargs -I{} bash -c 'echo SERVERLESS_APIGW_URL=https://{} > .apigw.tmp'
	@grep -q SERVERLESS_APIGW_URL .env || cat .apigw.tmp >> .env; rm -f .apigw.tmp
	@echo "API Gateway создан"

webhook_info: ## Получить информацию о webhook
	@echo "Информация о webhook:"
	curl --request POST --url "https://api.telegram.org/bot$(TELEGRAM_APITOKEN)/getWebhookInfo"

webhook_delete: ## Удалить webhook
	@echo "Удаление webhook..."
	curl --request POST --url "https://api.telegram.org/bot$(TELEGRAM_APITOKEN)/deleteWebhook"

webhook_create: webhook_delete ## Создать webhook
	@echo "Создание webhook..."
	curl --request POST --url "https://api.telegram.org/bot$(TELEGRAM_APITOKEN)/setWebhook" \
	  --header 'content-type: application/json' \
	  --data "{\"url\": \"$(SERVERLESS_APIGW_URL)\"}"
	@echo "Webhook создан: $(SERVERLESS_APIGW_URL)"

build: ## Собрать Docker образ
	@echo "Сборка Docker образа..."
	docker build -t cr.yandex/$(YC_IMAGE_REGISTRY_ID)/$(SERVERLESS_CONTAINER_NAME):latest .
	@echo "Образ собран: cr.yandex/$(YC_IMAGE_REGISTRY_ID)/$(SERVERLESS_CONTAINER_NAME):latest"

push: build ## Запушить образ в реестр
	@echo "Загрузка образа в Container Registry..."
	docker push cr.yandex/$(YC_IMAGE_REGISTRY_ID)/$(SERVERLESS_CONTAINER_NAME):latest
	@echo "Образ загружен в реестр"

deploy: push ## Деплой контейнера
	@echo "Деплой Serverless Container..."
	@sed 's/=.*/=/' .env > .env.example
	yc serverless container revision deploy \
	  --container-name $(SERVERLESS_CONTAINER_NAME) \
	  --image cr.yandex/$(YC_IMAGE_REGISTRY_ID)/$(SERVERLESS_CONTAINER_NAME):latest \
	  --service-account-id $(SERVICE_ACCOUNT_ID) \
	  --environment="TELEGRAM_APITOKEN=$(TELEGRAM_APITOKEN),TELEGRAM_BOT_TOKEN=$(TELEGRAM_APITOKEN),GOOGLE_SA_JSON_PATH=$(GOOGLE_SA_JSON_PATH),GOOGLE_SHEET_ID=$(GOOGLE_SHEET_ID),GOOGLE_SHEET_NAME=$(GOOGLE_SHEET_NAME),TIMEZONE=$(TIMEZONE),ADMIN_IDS=$(ADMIN_IDS)" \
	  --core-fraction 50 \
	  --memory 1GB \
	  --execution-timeout $(SERVERLESS_CONTAINER_EXEC_TIMEOUT)s
	@yc serverless container get --name $(SERVERLESS_CONTAINER_NAME) --format json | jq -r '.id' | xargs -I{} bash -c 'echo SERVERLESS_CONTAINER_ID={} > .scid.tmp'
	@grep -q SERVERLESS_CONTAINER_ID .env || cat .scid.tmp >> .env; rm -f .scid.tmp
	@echo "Контейнер задеплоен"

all: create deploy create_gw webhook_create ## Полный деплой (создать + деплой + API Gateway + webhook)
	@echo "Полный деплой завершен!"
	@echo "API Gateway URL: $(SERVERLESS_APIGW_URL)"
	@echo "Проверка webhook: make webhook_info"

logs: ## Показать логи контейнера
	@echo "Логи контейнера:"
	yc logging read --folder-id $(shell yc config list | sed -n 's/^folder-id:\s*//p') --resource-types serverless-container --since 1h

test: ## Тестировать webhook
	@echo "Тестирование webhook..."
	@if [ -z "$(SERVERLESS_APIGW_URL)" ]; then \
		echo "Ошибка: SERVERLESS_APIGW_URL не установлен. Сначала выполните: make all"; \
		exit 1; \
	fi
	curl -X POST "$(SERVERLESS_APIGW_URL)" \
	  -H "Content-Type: application/json" \
	  -d '{"update_id":0,"message":{"message_id":1,"from":{"id":123,"first_name":"Test"},"chat":{"id":123,"type":"private"},"date":1234567890,"text":"/start"}}'

clean: ## Очистить временные файлы
	@echo "Очистка временных файлов..."
	rm -f api-gw.yaml .apigw.tmp .scid.tmp
	@echo "Очистка завершена"
