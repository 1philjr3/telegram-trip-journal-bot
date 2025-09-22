# 🆓 ПОЛНОСТЬЮ БЕСПЛАТНЫЕ ВАРИАНТЫ ДЕПЛОЯ

## 🥇 Koyeb (100% бесплатно навсегда!)

**Лучший бесплатный вариант - без ограничений по времени!**

### Что делать:
1. **Зайдите на [koyeb.com](https://koyeb.com)**
2. **Sign up** → войдите через GitHub
3. **Create App** → **GitHub**
4. **Repository**: выберите `1philjr3/telegram-trip-journal-bot`
5. **Instance type**: выберите **"Nano"** (бесплатно)
6. **Environment Variables** → добавьте:

```
TELEGRAM_BOT_TOKEN=8337632073:AAHChPR4gUnpc4omV1NN92DqLBZBFC--iYE
GOOGLE_SHEET_ID=1kGgu5UsVydbbDPtmdMrakdVEvbFkxBRbcFTyACnNXIM
ADMIN_IDS=349866166
GOOGLE_SHEET_NAME=Лист1
TIMEZONE=Europe/Moscow
GOOGLE_SA_JSON_PATH=./service_account.json
GOOGLE_SERVICE_ACCOUNT_JSON=<JSON из service_account.json>
```

7. **Deploy** → готово!

**Плюсы Koyeb:**
- ✅ Полностью бесплатно навсегда
- ✅ Без ограничений по времени
- ✅ Автоматический деплой
- ✅ Встроенные логи

---

## 🥈 Fly.io (бесплатно до лимитов)

### Что делать:
1. **Зайдите на [fly.io](https://fly.io)**
2. **Sign up** → войдите через GitHub
3. **New App** → **Import from GitHub**
4. **Repository**: `1philjr3/telegram-trip-journal-bot`
5. **Secrets** → добавьте те же переменные
6. **Deploy**

**Лимиты:**
- 160 часов в месяц (5+ часов в день)
- 3 GB трафика

---

## 🥉 Render (750 часов бесплатно)

Если хотите попробовать Render как **Background Worker**:

1. **[render.com](https://render.com)** → **New +** → **Background Worker**
2. **Repository**: `1philjr3/telegram-trip-journal-bot`
3. **Start Command**: `python3 bot.py`
4. **Environment Variables**: добавьте переменные
5. **Secret Files**: добавьте `service_account.json`

---

## ⚡ Google Colab (запуск прямо сейчас!)

**Самый быстрый способ протестировать:**

1. **Откройте [colab.research.google.com](https://colab.research.google.com)**
2. **Создайте новый notebook**
3. **Вставьте и выполните код:**

```python
# Клонируем репозиторий
!git clone https://github.com/1philjr3/telegram-trip-journal-bot.git
%cd telegram-trip-journal-bot

# Устанавливаем зависимости
!pip install -r requirements.txt

# Настраиваем переменные окружения
import os
os.environ['TELEGRAM_BOT_TOKEN'] = '8337632073:AAHChPR4gUnpc4omV1NN92DqLBZBFC--iYE'
os.environ['GOOGLE_SHEET_ID'] = '1kGgu5UsVydbbDPtmdMrakdVEvbFkxBRbcFTyACnNXIM'
os.environ['ADMIN_IDS'] = '349866166'
os.environ['GOOGLE_SHEET_NAME'] = 'Лист1'
os.environ['TIMEZONE'] = 'Europe/Moscow'
os.environ['GOOGLE_SA_JSON_PATH'] = './service_account.json'

# Создаем service_account.json (вставьте ваш JSON)
service_account_json = '''
ВСТАВЬТЕ_СЮДА_СОДЕРЖИМОЕ_ВАШЕГО_ФАЙЛА_service_account_json
'''

with open('service_account.json', 'w') as f:
    f.write(service_account_json)

# Запускаем бота
!python3 bot.py
```

**Colab работает 12 часов подряд, потом нужно перезапустить.**

---

## 🐳 Oracle Cloud (навсегда бесплатно!)

**Самый мощный бесплатный вариант:**

### Что получаете:
- ✅ **2 виртуальные машины** навсегда бесплатно
- ✅ **1 GB RAM** каждая
- ✅ **Без ограничений по времени**
- ✅ **Полный root доступ**

### Что делать:
1. **Зарегистрируйтесь на [oracle.com/cloud](https://oracle.com/cloud)**
2. **Создайте виртуальную машину** (Compute → Instances)
3. **Подключитесь по SSH**
4. **Установите Docker и запустите бота:**

```bash
# Установка Docker
sudo apt update
sudo apt install docker.io -y
sudo systemctl start docker

# Клонируем и запускаем
git clone https://github.com/1philjr3/telegram-trip-journal-bot.git
cd telegram-trip-journal-bot

# Создаем .env файл
cat > .env << EOF
TELEGRAM_BOT_TOKEN=8337632073:AAHChPR4gUnpc4omV1NN92DqLBZBFC--iYE
GOOGLE_SHEET_ID=1kGgu5UsVydbbDPtmdMrakdVEvbFkxBRbcFTyACnNXIM
ADMIN_IDS=349866166
GOOGLE_SHEET_NAME=Лист1
TIMEZONE=Europe/Moscow
GOOGLE_SA_JSON_PATH=./service_account.json
EOF

# Создаем service_account.json (вставьте ваш JSON)
cat > service_account.json << 'EOF'
{ваш JSON}
EOF

# Собираем и запускаем Docker
sudo docker build -t telegram-bot .
sudo docker run -d --restart=always telegram-bot
```

---

## 🎯 Gitpod (бесплатно 50 часов в месяц)

**Онлайн IDE с хостингом:**

1. **Откройте [gitpod.io](https://gitpod.io)**
2. **Войдите через GitHub**
3. **Откройте workspace**: `https://gitpod.io/#https://github.com/1philjr3/telegram-trip-journal-bot`
4. **В терминале выполните:**

```bash
# Создаем .env
cp env_example.txt .env
# Отредактируйте .env с вашими данными

# Создаем service_account.json
# Вставьте ваш JSON в файл

# Запускаем
python3 bot.py
```

---

## 🌟 GitHub Codespaces (60 часов бесплатно)

**Прямо в GitHub:**

1. **Откройте ваш репозиторий на GitHub**
2. **Нажмите зеленую кнопку "Code"**
3. **Вкладка "Codespaces"** → **"Create codespace"**
4. **В терминале:**

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp env_example.txt .env
# Отредактируйте .env

# Создайте service_account.json
# Вставьте ваш JSON

# Запуск
python3 bot.py
```

---

## 🏆 МОЯ РЕКОМЕНДАЦИЯ для 100% бесплатного хостинга:

### **Koyeb.com** - идеальный вариант!

**Почему:**
- ✅ **Полностью бесплатно** навсегда
- ✅ **Без ограничений** по времени работы
- ✅ **Автоматический деплой** из GitHub
- ✅ **Простая настройка** - 3 клика
- ✅ **Встроенные логи** и мониторинг
- ✅ **Автоматический перезапуск** при сбоях

### Буквально 3 шага:
1. **Зарегистрироваться** на koyeb.com через GitHub
2. **Выбрать** ваш репозиторий
3. **Добавить** переменные окружения

**И ВСЁ!** Бот будет работать бесплатно 24/7! 🚀

---

## 💡 Если нужна максимальная надежность:

**Oracle Cloud Always Free** - настоящие виртуальные машины навсегда бесплатно, но требует больше настройки.

**Koyeb** - самый простой для начинающих!
