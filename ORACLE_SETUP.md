# 🏆 Oracle Cloud Always Free - Пошаговая настройка

**Самый лучший бесплатный вариант - 2 виртуальные машины навсегда бесплатно!**

## 🎯 Что получаете НАВСЕГДА БЕСПЛАТНО:

- ✅ **2 виртуальные машины** (AMD или ARM)
- ✅ **1 GB RAM** каждая
- ✅ **1/8 OCPU** (процессор)
- ✅ **47 GB Boot Volume**
- ✅ **200 GB исходящего трафика/месяц**
- ✅ **Без ограничений по времени**
- ✅ **Полный root доступ**

## 📋 Пошаговая настройка:

### Шаг 1: Регистрация
1. **Перейдите на [oracle.com/cloud](https://oracle.com/cloud)**
2. **Нажмите "Start for free"**
3. **Заполните форму регистрации**
   - Выберите страну: Россия
   - Тип аккаунта: Personal Use
   - **Важно:** Потребуется банковская карта для верификации, но списаний не будет!

### Шаг 2: Создание виртуальной машины
1. **Войдите в Oracle Cloud Console**
2. **Перейдите в "Compute" → "Instances"**
3. **Нажмите "Create Instance"**

### Шаг 3: Настройка VM
**Основные параметры:**
- **Name**: `telegram-bot-server`
- **Availability Domain**: любой
- **Image**: `Ubuntu 22.04` (рекомендуется)
- **Shape**: `VM.Standard.E2.1.Micro` (Always Free eligible)

**Networking:**
- **VCN**: оставьте по умолчанию
- **Subnet**: Public subnet
- **Assign public IP**: ✅ включено

**SSH Keys:**
- **Generate SSH key pair**: скачайте приватный ключ
- Или загрузите свой публичный ключ

### Шаг 4: Подключение по SSH
```bash
# Замените YOUR_PRIVATE_KEY.key и YOUR_PUBLIC_IP
chmod 600 YOUR_PRIVATE_KEY.key
ssh -i YOUR_PRIVATE_KEY.key ubuntu@YOUR_PUBLIC_IP
```

### Шаг 5: Настройка сервера
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и необходимые пакеты
sudo apt install python3 python3-pip git nano htop -y

# Клонируем репозиторий
git clone https://github.com/1philjr3/telegram-trip-journal-bot.git
cd telegram-trip-journal-bot

# Устанавливаем зависимости Python
pip3 install -r requirements.txt
```

### Шаг 6: Настройка конфигурации
```bash
# Создаем .env файл
nano .env
```

**Вставьте в .env:**
```
TELEGRAM_BOT_TOKEN=8337632073:AAHChPR4gUnpc4omV1NN92DqLBZBFC--iYE
GOOGLE_SHEET_ID=1kGgu5UsVydbbDPtmdMrakdVEvbFkxBRbcFTyACnNXIM
ADMIN_IDS=349866166
GOOGLE_SHEET_NAME=Лист1
TIMEZONE=Europe/Moscow
GOOGLE_SA_JSON_PATH=./service_account.json
```

```bash
# Создаем service_account.json
nano service_account.json
```

**Вставьте в service_account.json содержимое вашего локального файла**

### Шаг 7: Запуск бота как сервис
```bash
# Создаем systemd сервис
sudo nano /etc/systemd/system/telegram-bot.service
```

**Содержимое файла сервиса:**
```ini
[Unit]
Description=Telegram Trip Journal Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-trip-journal-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=/home/ubuntu/telegram-trip-journal-bot

[Install]
WantedBy=multi-user.target
```

```bash
# Активируем и запускаем сервис
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service

# Проверяем статус
sudo systemctl status telegram-bot.service

# Смотрим логи
sudo journalctl -u telegram-bot.service -f
```

### Шаг 8: Настройка автозапуска
```bash
# Убеждаемся, что сервис запускается при перезагрузке
sudo systemctl is-enabled telegram-bot.service

# Если нужно, включаем автозапуск
sudo systemctl enable telegram-bot.service
```

## 🔧 Полезные команды для управления:

```bash
# Перезапуск бота
sudo systemctl restart telegram-bot.service

# Остановка бота
sudo systemctl stop telegram-bot.service

# Просмотр логов
sudo journalctl -u telegram-bot.service -f

# Обновление кода
cd telegram-trip-journal-bot
git pull
sudo systemctl restart telegram-bot.service

# Проверка ресурсов
htop
df -h
free -h
```

## 🛡️ Настройка безопасности:

```bash
# Настройка firewall (рекомендуется)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow out 443
sudo ufw allow out 80

# Обновление системы
sudo apt update && sudo apt upgrade -y
```

## ✅ Проверка работы:

1. **Статус сервиса**: `sudo systemctl status telegram-bot.service`
2. **Логи**: `sudo journalctl -u telegram-bot.service -f`
3. **Тест бота**: Напишите `/start` в Telegram
4. **Проверка ресурсов**: `htop` (должно использовать ~100-200MB RAM)

## 🎉 Результат:

- ✅ **Бот работает 24/7**
- ✅ **Автоматический перезапуск** при сбоях
- ✅ **Автозапуск** при перезагрузке сервера
- ✅ **Навсегда бесплатно**
- ✅ **Полный контроль** над сервером

## 🔄 Обслуживание:

- **Раз в месяц**: `sudo apt update && sudo apt upgrade -y`
- **При обновлении кода**: `git pull && sudo systemctl restart telegram-bot.service`
- **Мониторинг**: Проверяйте логи периодически

## 💡 Советы:

- **Сделайте снимок** (snapshot) VM после настройки
- **Настройте мониторинг** через Oracle Cloud Console
- **Сохраните SSH ключи** в безопасном месте

**Этот способ даст вам полноценный сервер навсегда бесплатно!** 🚀
