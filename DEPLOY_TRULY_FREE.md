# 💯 ДЕЙСТВИТЕЛЬНО БЕСПЛАТНЫЕ ВАРИАНТЫ (без скрытых платежей!)

## 🥇 Oracle Cloud Always Free (ЛУЧШИЙ ВЫБОР!)

**Навсегда бесплатно, без ограничений по времени!**

### Что получаете:
- ✅ **2 виртуальные машины** (1GB RAM каждая)
- ✅ **Навсегда бесплатно** (не trial)
- ✅ **Без ограничений по времени**
- ✅ **200 GB исходящего трафика**
- ✅ **Полный root доступ**

### Настройка (10 минут):
1. **Зарегистрируйтесь на [oracle.com/cloud](https://oracle.com/cloud)**
2. **Создайте Compute Instance** (VM)
3. **Подключитесь по SSH**
4. **Выполните команды:**

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и Git
sudo apt install python3 python3-pip git -y

# Клонируем репозиторий
git clone https://github.com/1philjr3/telegram-trip-journal-bot.git
cd telegram-trip-journal-bot

# Устанавливаем зависимости
pip3 install -r requirements.txt

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
nano service_account.json
# Вставьте содержимое вашего локального файла

# Запускаем бота в фоне
nohup python3 bot.py > bot.log 2>&1 &

# Проверяем, что работает
tail -f bot.log
```

**Результат:** Бот работает 24/7 навсегда бесплатно!

---

## 🥈 Google Colab (мгновенный запуск!)

**Самый быстрый способ протестировать прямо сейчас:**

### Что делать:
1. **Откройте [colab.research.google.com](https://colab.research.google.com)**
2. **Создайте новый notebook**
3. **Вставьте и выполните:**

```python
# Клонируем репозиторий
!git clone https://github.com/1philjr3/telegram-trip-journal-bot.git
%cd telegram-trip-journal-bot

# Устанавливаем зависимости
!pip install -r requirements.txt

# Настраиваем переменные
import os
os.environ['TELEGRAM_BOT_TOKEN'] = '8337632073:AAHChPR4gUnpc4omV1NN92DqLBZBFC--iYE'
os.environ['GOOGLE_SHEET_ID'] = '1kGgu5UsVydbbDPtmdMrakdVEvbFkxBRbcFTyACnNXIM'
os.environ['ADMIN_IDS'] = '349866166'
os.environ['GOOGLE_SHEET_NAME'] = 'Лист1'
os.environ['TIMEZONE'] = 'Europe/Moscow'
os.environ['GOOGLE_SA_JSON_PATH'] = './service_account.json'

# Создаем service_account.json
service_json = """
ВСТАВЬТЕ_СЮДА_СОДЕРЖИМОЕ_ВАШЕГО_service_account.json
"""
with open('service_account.json', 'w') as f:
    f.write(service_json)

# Запускаем бота
!python3 bot.py
```

**Ограничения:** 12 часов работы, потом нужно перезапустить

---

## 🥉 GitHub Codespaces (60 часов/месяц)

**Встроено в GitHub:**

### Что делать:
1. **Откройте ваш репозиторий на GitHub**
2. **Нажмите зеленую кнопку "Code"**
3. **Вкладка "Codespaces"** → **"Create codespace"**
4. **В терминале выполните:**

```bash
# Установка зависимостей
pip install -r requirements.txt

# Создание конфигурации
cp env_example.txt .env
# Отредактируйте .env с вашими данными

# Создайте service_account.json
# Вставьте ваш JSON

# Запуск
python3 bot.py
```

**Лимит:** 60 часов в месяц (2 часа в день)

---

## 🏆 Gitpod (50 часов/месяц)

### Что делать:
1. **Откройте [gitpod.io](https://gitpod.io)**
2. **Войдите через GitHub**
3. **Откройте workspace**: 
   ```
   https://gitpod.io/#https://github.com/1philjr3/telegram-trip-journal-bot
   ```
4. **Настройте и запустите** (как в Codespaces)

---

## 🚀 Replit (бесплатный план)

### Что делать:
1. **Зайдите на [replit.com](https://replit.com)**
2. **Import from GitHub**: `1philjr3/telegram-trip-journal-bot`
3. **Настройте Secrets** (переменные окружения)
4. **Нажмите Run**

**Ограничения:** Засыпает при бездействии

---

## 🎯 МОЯ РЕКОМЕНДАЦИЯ:

### **Oracle Cloud Always Free** - лучший вариант!

**Почему:**
- ✅ **Действительно навсегда бесплатно**
- ✅ **Полноценная виртуальная машина**
- ✅ **Без ограничений по времени**
- ✅ **24/7 работа**
- ✅ **Ваш Python код работает как есть**

**Единственный минус:** Нужно потратить 10 минут на настройку SSH и команды Linux.

### **Если нужно ПРЯМО СЕЙЧАС:**

**Google Colab** - запустите бота за 1 минуту, пока настраиваете Oracle Cloud!

## 📋 План действий:

1. **Сейчас:** Запустите в Google Colab для тестирования
2. **Потом:** Настройте Oracle Cloud для постоянной работы
3. **Результат:** Бот работает бесплатно 24/7 навсегда!

Какой вариант попробуете?
