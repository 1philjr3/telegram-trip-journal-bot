import asyncio
import logging
import os
from typing import Optional, List
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from models import TripEntry
from sheets_client import GoogleSheetsClient
from users_repo import UsersRepository
from utils_time import TimeUtils


# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация компонентов
bot = Bot(token=os.getenv("TELEGRAM_APITOKEN"))
dp = Dispatcher(storage=MemoryStorage())

# Глобальные объекты
users_repo = UsersRepository(
    service_account_path=os.getenv("GOOGLE_SA_JSON_PATH", "./service_account.json"),
    sheet_id=os.getenv("GOOGLE_SHEET_ID"),
    users_sheet_name="Пользователи"
)
time_utils = TimeUtils(os.getenv("TIMEZONE", "Europe/Moscow"))
sheets_client = GoogleSheetsClient(
    service_account_path=os.getenv("GOOGLE_SA_JSON_PATH", "./service_account.json"),
    sheet_id=os.getenv("GOOGLE_SHEET_ID"),
    sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Лист1")
)

# ==== Фото-поток: OCR одометра и делений топлива ====
# Временно отключено для отладки
extract_from_image = None
PanelReading = None

def get_env_roi(name: str, default: str) -> tuple:
    val = os.getenv(name, default)
    try:
        x, y, w, h = [int(v.strip()) for v in val.split(',')]
        return (x, y, w, h)
    except Exception:
        return tuple(int(v) for v in default.split(','))

FUEL_BARS = int(os.getenv("FUEL_BARS", "8"))
LITERS_PER_BAR = float(os.getenv("LITERS_PER_BAR", "6.25"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.6"))

PHOTO_CONFIRM_PREFIX = "confirm_photo"
PHOTO_MANUAL_PREFIX = "manual_photo"
PHOTO_RETAKE_PREFIX = "retake_photo"

def build_photo_confirm_kb(user_id: int, odo: int, bars: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Верно", callback_data=f"{PHOTO_CONFIRM_PREFIX}:{user_id}:{odo}:{bars}")
    kb.button(text="✏️ Ввести вручную", callback_data=f"{PHOTO_MANUAL_PREFIX}:{user_id}")
    kb.button(text="📷 Перефото", callback_data=f"{PHOTO_RETAKE_PREFIX}:{user_id}")
    kb.adjust(1, 2)
    return kb.as_markup()

@dp.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    if extract_from_image is None:
        await message.answer("OCR модуль не активен. Сообщите администратору.")
        return

    if not users_repo.is_registered(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь: /start")
        return

    try:
        file = await bot.get_file(message.photo[-1].file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_bytes = file_bytes.read()

        reading: PanelReading = await asyncio.to_thread(extract_from_image, image_bytes)

        if reading is None or reading.odometer_km is None or reading.fuel_bars is None:
            await message.answer(
                "Не смог разобрать показания. Можем перейти на ручной ввод?",
                reply_markup=build_photo_confirm_kb(message.from_user.id, 0, 0)
            )
            return

        liters = round(reading.fuel_bars * LITERS_PER_BAR, 2)

        text = (
            "Нашёл:\n"
            f"• Пробег: <b>{reading.odometer_km}</b> км\n"
            f"• Остаток: <b>{reading.fuel_bars}</b> × {LITERS_PER_BAR} = <b>{liters}</b> л\n\n"
            "Всё верно?"
        )

        if reading.confidence < MIN_CONFIDENCE:
            text = "<i>Низкая уверенность распознавания.</i>\n" + text

        await message.answer(
            text,
            reply_markup=build_photo_confirm_kb(message.from_user.id, reading.odometer_km, reading.fuel_bars),
            parse_mode="HTML"
        )

        await state.update_data(last_photo_file_id=message.photo[-1].file_id)

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await message.answer("❌ Ошибка обработки фото. Попробуйте ещё раз или введите вручную.")


@dp.callback_query(F.data.startswith(PHOTO_CONFIRM_PREFIX + ":"))
async def handle_photo_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        _, uid, odo, bars = callback.data.split(":")
        odo = int(odo)
        bars = int(bars)
        liters = round(bars * LITERS_PER_BAR, 2)

        data = await state.get_data()
        file_id = data.get("last_photo_file_id")

        ok = await asyncio.to_thread(
            sheets_client.append_measurement,
            callback.from_user.id,
            odo,
            bars,
            liters,
            "photo",
            file_id,
        )
        if ok:
            await callback.message.edit_text(
                f"✅ Записал. Одометр: <b>{odo}</b> км. Остаток: <b>{liters}</b> л.",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text("❌ Не удалось сохранить запись. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка подтверждения фото: {e}")
        await callback.message.edit_text("❌ Ошибка сохранения.")


@dp.callback_query(F.data.startswith(PHOTO_MANUAL_PREFIX + ":"))
async def handle_photo_manual(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Введите одометр (км) и число делений (0–8) одной строкой, напр.: 55698 6"
    )
    await state.set_state(PhotoStates.waiting_manual_odo_bars)
    await state.update_data(photo_manual=True)


@dp.message(F.text, StateFilter(PhotoStates.waiting_manual_odo_bars))
async def handle_photo_manual_input(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("photo_manual"):
        return

    try:
        parts = message.text.strip().split()
        odo = int(parts[0])
        bars = int(parts[1])
        if bars < 0 or bars > FUEL_BARS:
            raise ValueError
        liters = round(bars * LITERS_PER_BAR, 2)
        ok = await asyncio.to_thread(
            sheets_client.append_measurement,
            message.from_user.id,
            odo,
            bars,
            liters,
            "manual",
            None,
        )
        if ok:
            await message.answer(
                f"✅ Записал. Одометр: <b>{odo}</b> км. Остаток: <b>{liters}</b> л.",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Не удалось сохранить запись. Попробуйте позже.")
    except Exception:
        await message.answer("❌ Формат: 55698 6 (одометр и деления 0–8)")
        return
    finally:
        await state.update_data(photo_manual=False)


@dp.callback_query(F.data.startswith(PHOTO_RETAKE_PREFIX + ":"))
async def handle_photo_retake(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("📷 Пришлите новое фото приборной панели (без бликов, не под углом).")

# Админы
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]


class TripStates(StatesGroup):
    """Состояния FSM для создания новой записи"""
    waiting_start_time = State()
    waiting_odometer_start = State()
    waiting_end_time = State()
    waiting_odometer_end = State()
    waiting_project = State()
    waiting_address = State()
    waiting_comment = State()
    waiting_confirmation = State()


class EditStates(StatesGroup):
    """Состояния FSM для редактирования записи"""
    waiting_field_choice = State()
    waiting_new_value = State()

class PhotoStates(StatesGroup):
    """Состояния FSM для фото-потока"""
    waiting_manual_odo_bars = State()


async def send_main_menu(message: Message):
    """Отправляет главное меню"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🆕 Новая запись", callback_data="new_entry")
    keyboard.button(text="📋 Последние записи", callback_data="last_entries")
    keyboard.button(text="✏️ Редактировать последнюю", callback_data="edit_last")
    keyboard.button(text="ℹ️ Помощь", callback_data="help")
    
    if message.from_user.id in ADMIN_IDS:
        keyboard.button(text="👑 Экспорт (Админ)", callback_data="export")
    
    keyboard.adjust(1, 2, 1, 1)
    
    await message.answer(
        "🚗 <b>Журнал поездок инженера</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    if not users_repo.is_registered(user_id):
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для начала работы необходимо пройти регистрацию.\n"
            "📝 Введите ваше ФИО (Фамилия Имя Отчество):"
        )
        return
    
    user = users_repo.get_user(user_id)
    await message.answer(
        f"👋 Добро пожаловать, <b>{user.full_name}</b>!\n\n"
        f"Вы зарегистрированы с {datetime.fromisoformat(user.created_at.replace('Z', '+00:00')).strftime('%d.%m.%Y')}",
        parse_mode="HTML"
    )
    await send_main_menu(message)


@dp.message(F.text, StateFilter(None))
async def handle_registration(message: Message):
    """Обработчик регистрации пользователя"""
    user_id = message.from_user.id
    
    if users_repo.is_registered(user_id):
        await send_main_menu(message)
        return
    
    full_name = message.text.strip()
    
    # Простая валидация ФИО
    if len(full_name) < 3 or len(full_name.split()) < 2:
        await message.answer(
            "❌ Пожалуйста, введите корректное ФИО (минимум Имя Фамилия):"
        )
        return
    
    # Регистрируем пользователя
    users_repo.register_user(user_id, full_name)
    
    await message.answer(
        f"✅ <b>Регистрация завершена!</b>\n\n"
        f"👤 {full_name}\n"
        f"🆔 Ваш ID: {user_id}\n\n"
        f"Теперь вы можете пользоваться ботом!",
        parse_mode="HTML"
    )
    await send_main_menu(message)


@dp.message(Command("new"))
async def cmd_new_entry(message: Message, state: FSMContext):
    """Обработчик команды /new - создание новой записи"""
    user_id = message.from_user.id
    
    if not users_repo.is_registered(user_id):
        await message.answer("❌ Сначала необходимо зарегистрироваться. Используйте /start")
        return
    
    await start_new_entry(message, state)


@dp.callback_query(F.data == "new_entry")
async def callback_new_entry(callback: CallbackQuery, state: FSMContext):
    """Callback для создания новой записи"""
    await callback.answer()
    await start_new_entry(callback.message, state, edit_message=True)


async def start_new_entry(message: Message, state: FSMContext, edit_message: bool = False):
    """Начинает процесс создания новой записи"""
    await state.clear()
    await state.set_state(TripStates.waiting_start_time)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⏰ Сейчас", callback_data="time_now")
    keyboard.button(text="✏️ Ввести вручную", callback_data="time_manual")
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    keyboard.adjust(2, 1)
    
    text = (
        "🕐 <b>Время начала поездки</b>\n\n"
        "Выберите время начала:\n"
        "• <b>Сейчас</b> - текущее время\n"
        "• <b>Ввести вручную</b> - в формате ДД.ММ.ГГГГ ЧЧ:ММ или ЧЧ:ММ"
    )
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "time_now", StateFilter(TripStates.waiting_start_time))
async def callback_start_time_now(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора текущего времени начала"""
    await callback.answer()
    
    current_time = time_utils.get_current_datetime()
    await state.update_data(start_time=current_time)
    
    date_str, time_str = time_utils.format_datetime_for_sheets(current_time)
    
    await callback.message.edit_text(
        f"✅ Время начала: <b>{time_utils.format_datetime_for_display(current_time)}</b>\n\n"
        f"🛣️ Введите показания одометра на <b>начало</b> поездки (в километрах):",
        parse_mode="HTML"
    )
    
    await state.set_state(TripStates.waiting_odometer_start)


@dp.callback_query(F.data == "time_manual", StateFilter(TripStates.waiting_start_time))
async def callback_start_time_manual(callback: CallbackQuery, state: FSMContext):
    """Обработчик ручного ввода времени начала"""
    await callback.answer()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await callback.message.edit_text(
        "🕐 <b>Ввод времени начала</b>\n\n"
        "Введите время начала в одном из форматов:\n"
        "• <code>ДД.ММ.ГГГГ ЧЧ:ММ</code> (например: 21.09.2024 14:30)\n"
        "• <code>ЧЧ:ММ</code> (например: 14:30) - для сегодняшней даты\n"
        "• <code>сейчас</code> - текущее время",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@dp.message(F.text, StateFilter(TripStates.waiting_start_time))
async def handle_start_time_input(message: Message, state: FSMContext):
    """Обработчик ввода времени начала"""
    start_time = time_utils.parse_datetime_input(message.text)
    
    if start_time is None:
        await message.answer(
            "❌ Неправильный формат времени!\n\n"
            "Используйте один из форматов:\n"
            "• <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "• <code>ЧЧ:ММ</code>\n"
            "• <code>сейчас</code>",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(start_time=start_time)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await message.answer(
        f"✅ Время начала: <b>{time_utils.format_datetime_for_display(start_time)}</b>\n\n"
        f"🛣️ Введите показания одометра на <b>начало</b> поездки (в километрах):",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(TripStates.waiting_odometer_start)


@dp.message(F.text, StateFilter(TripStates.waiting_odometer_start))
async def handle_odometer_start(message: Message, state: FSMContext):
    """Обработчик ввода начального одометра"""
    try:
        odometer_start = int(message.text.strip())
        if odometer_start < 0:
            raise ValueError("Отрицательное значение")
            
        await state.update_data(odometer_start=odometer_start)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⏰ Сейчас", callback_data="end_time_now")
        keyboard.button(text="✏️ Ввести вручную", callback_data="end_time_manual")
        keyboard.button(text="❌ Отмена", callback_data="cancel")
        keyboard.adjust(2, 1)
        
        await message.answer(
            f"✅ Одометр начала: <b>{odometer_start:,} км</b>\n\n"
            f"🕐 <b>Время окончания поездки</b>\n\n"
            f"Выберите время окончания:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
        await state.set_state(TripStates.waiting_end_time)
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число километров (целое положительное число):"
        )


@dp.callback_query(F.data == "end_time_now", StateFilter(TripStates.waiting_end_time))
async def callback_end_time_now(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора текущего времени окончания"""
    await callback.answer()
    
    current_time = time_utils.get_current_datetime()
    data = await state.get_data()
    start_time = data['start_time']
    
    # Проверяем, что время окончания больше времени начала
    if not time_utils.validate_time_sequence(start_time, current_time):
        await callback.message.edit_text(
            "❌ Время окончания не может быть раньше времени начала!\n\n"
            "Пожалуйста, выберите корректное время окончания или измените время начала.",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(end_time=current_time)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await callback.message.edit_text(
        f"✅ Время окончания: <b>{time_utils.format_datetime_for_display(current_time)}</b>\n"
        f"⏱️ Продолжительность: <b>{time_utils.format_duration(start_time, current_time)}</b>\n\n"
        f"🛣️ Введите показания одометра на <b>конец</b> поездки (в километрах):",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(TripStates.waiting_odometer_end)


@dp.callback_query(F.data == "end_time_manual", StateFilter(TripStates.waiting_end_time))
async def callback_end_time_manual(callback: CallbackQuery, state: FSMContext):
    """Обработчик ручного ввода времени окончания"""
    await callback.answer()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await callback.message.edit_text(
        "🕐 <b>Ввод времени окончания</b>\n\n"
        "Введите время окончания в одном из форматов:\n"
        "• <code>ДД.ММ.ГГГГ ЧЧ:ММ</code> (например: 21.09.2024 16:30)\n"
        "• <code>ЧЧ:ММ</code> (например: 16:30) - для сегодняшней даты\n"
        "• <code>сейчас</code> - текущее время",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@dp.message(F.text, StateFilter(TripStates.waiting_end_time))
async def handle_end_time_input(message: Message, state: FSMContext):
    """Обработчик ввода времени окончания"""
    end_time = time_utils.parse_datetime_input(message.text)
    
    if end_time is None:
        await message.answer(
            "❌ Неправильный формат времени!\n\n"
            "Используйте один из форматов:\n"
            "• <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "• <code>ЧЧ:ММ</code>\n"
            "• <code>сейчас</code>",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    start_time = data['start_time']
    
    # Проверяем последовательность времени
    if not time_utils.validate_time_sequence(start_time, end_time):
        await message.answer(
            "❌ Время окончания не может быть раньше времени начала!\n\n"
            f"Время начала: <b>{time_utils.format_datetime_for_display(start_time)}</b>\n"
            f"Время окончания: <b>{time_utils.format_datetime_for_display(end_time)}</b>\n\n"
            "Пожалуйста, введите корректное время окончания:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(end_time=end_time)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await message.answer(
        f"✅ Время окончания: <b>{time_utils.format_datetime_for_display(end_time)}</b>\n"
        f"⏱️ Продолжительность: <b>{time_utils.format_duration(start_time, end_time)}</b>\n\n"
        f"🛣️ Введите показания одометра на <b>конец</b> поездки (в километрах):",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(TripStates.waiting_odometer_end)


@dp.message(F.text, StateFilter(TripStates.waiting_odometer_end))
async def handle_odometer_end(message: Message, state: FSMContext):
    """Обработчик ввода конечного одометра"""
    try:
        odometer_end = int(message.text.strip())
        if odometer_end < 0:
            raise ValueError("Отрицательное значение")
        
        data = await state.get_data()
        odometer_start = data['odometer_start']
        
        if odometer_end < odometer_start:
            await message.answer(
                f"❌ Конечный одометр ({odometer_end:,} км) не может быть меньше начального ({odometer_start:,} км)!\n\n"
                f"Введите корректное значение:"
            )
            return
        
        await state.update_data(odometer_end=odometer_end)
        
        distance_km = odometer_end - odometer_start
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⏭️ Пропустить", callback_data="skip_project")
        keyboard.button(text="❌ Отмена", callback_data="cancel")
        keyboard.adjust(1, 1)
        
        await message.answer(
            f"✅ Одометр окончания: <b>{odometer_end:,} км</b>\n"
            f"📏 Пробег: <b>{distance_km:,} км</b>\n\n"
            f"🏗️ Введите название проекта (необязательно):",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
        await state.set_state(TripStates.waiting_project)
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число километров (целое положительное число):"
        )


@dp.callback_query(F.data == "skip_project", StateFilter(TripStates.waiting_project))
async def callback_skip_project(callback: CallbackQuery, state: FSMContext):
    """Пропуск поля проекта"""
    await callback.answer()
    await state.update_data(project="")
    await ask_address(callback.message, state, edit_message=True)


@dp.message(F.text, StateFilter(TripStates.waiting_project))
async def handle_project(message: Message, state: FSMContext):
    """Обработчик ввода проекта"""
    project = message.text.strip()
    await state.update_data(project=project)
    await ask_address(message, state)


async def ask_address(message: Message, state: FSMContext, edit_message: bool = False):
    """Запрашивает адрес"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⏭️ Пропустить", callback_data="skip_address")
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    keyboard.adjust(1, 1)
    
    text = "📍 Введите адрес назначения (необязательно):"
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard.as_markup())
    else:
        await message.answer(text, reply_markup=keyboard.as_markup())
    
    await state.set_state(TripStates.waiting_address)


@dp.callback_query(F.data == "skip_address", StateFilter(TripStates.waiting_address))
async def callback_skip_address(callback: CallbackQuery, state: FSMContext):
    """Пропуск поля адреса"""
    await callback.answer()
    await state.update_data(address="")
    await ask_comment(callback.message, state, edit_message=True)


@dp.message(F.text, StateFilter(TripStates.waiting_address))
async def handle_address(message: Message, state: FSMContext):
    """Обработчик ввода адреса"""
    address = message.text.strip()
    await state.update_data(address=address)
    await ask_comment(message, state)


async def ask_comment(message: Message, state: FSMContext, edit_message: bool = False):
    """Запрашивает комментарий"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    text = (
        "💬 <b>Комментарий</b>\n\n"
        "Введите комментарий к поездке.\n"
        "Можно вставить текст из письма или добавить дополнительную информацию:"
    )
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    
    await state.set_state(TripStates.waiting_comment)


@dp.message(F.text, StateFilter(TripStates.waiting_comment))
async def handle_comment(message: Message, state: FSMContext):
    """Обработчик ввода комментария"""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показывает экран подтверждения"""
    data = await state.get_data()
    user = users_repo.get_user(message.from_user.id)
    
    start_time = data['start_time']
    end_time = data['end_time']
    odometer_start = data['odometer_start']
    odometer_end = data['odometer_end']
    distance_km = odometer_end - odometer_start
    project = data.get('project', '')
    address = data.get('address', '')
    comment = data['comment']
    
    # Форматируем для отображения
    start_display = time_utils.format_datetime_for_display(start_time)
    end_display = time_utils.format_datetime_for_display(end_time)
    duration = time_utils.format_duration(start_time, end_time)
    
    confirmation_text = (
        "📋 <b>Подтверждение записи</b>\n\n"
        f"👤 <b>Инженер:</b> {user.full_name}\n"
        f"🕐 <b>Начало:</b> {start_display}\n"
        f"🕑 <b>Окончание:</b> {end_display}\n"
        f"⏱️ <b>Продолжительность:</b> {duration}\n"
        f"🛣️ <b>Одометр начало:</b> {odometer_start:,} км\n"
        f"🛣️ <b>Одометр окончание:</b> {odometer_end:,} км\n"
        f"📏 <b>Пробег:</b> {distance_km:,} км\n"
    )
    
    if project:
        confirmation_text += f"🏗️ <b>Проект:</b> {project}\n"
    
    if address:
        confirmation_text += f"📍 <b>Адрес:</b> {address}\n"
    
    if comment:
        confirmation_text += f"💬 <b>Комментарий:</b> {comment[:100]}{'...' if len(comment) > 100 else ''}\n"
    
    confirmation_text += "\n<i>Все данные корректны?</i>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="confirm_save")
    keyboard.button(text="🔙 Назад", callback_data="go_back")
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    keyboard.adjust(1, 2)
    
    await message.answer(
        confirmation_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(TripStates.waiting_confirmation)


@dp.callback_query(F.data == "confirm_save", StateFilter(TripStates.waiting_confirmation))
async def callback_confirm_save(callback: CallbackQuery, state: FSMContext):
    """Сохранение записи в Google Sheets"""
    await callback.answer()
    
    data = await state.get_data()
    user = users_repo.get_user(callback.from_user.id)
    
    # Создаем объект записи
    start_time = data['start_time']
    end_time = data['end_time']
    start_date, start_time_str = time_utils.format_datetime_for_sheets(start_time)
    end_date, end_time_str = time_utils.format_datetime_for_sheets(end_time)
    
    trip_entry = TripEntry(
        date=start_date,
        time_start=start_time_str,
        time_end=end_time_str,
        odometer_start=data['odometer_start'],
        odometer_end=data['odometer_end'],
        distance_km=data['odometer_end'] - data['odometer_start'],
        engineer=user.full_name,
        project=data.get('project', ''),
        address=data.get('address', ''),
        comment=data['comment'],
        created_at=time_utils.get_utc_iso_string(),
        author_tg_id=callback.from_user.id
    )
    
    # Пытаемся сохранить в Google Sheets
    try:
        success = sheets_client.append_row(trip_entry)
        
        if success:
            await callback.message.edit_text(
                "✅ <b>Запись успешно добавлена!</b>\n\n"
                f"📏 Пробег: <b>{trip_entry.distance_km:,} км</b>\n"
                f"🕐 {time_utils.format_datetime_for_display(start_time)} - "
                f"{time_utils.format_datetime_for_display(end_time)}\n\n"
                f"Запись добавлена в Google Sheets.",
                parse_mode="HTML"
            )
            
            await state.clear()
            
            # Показываем главное меню через 3 секунды
            await asyncio.sleep(3)
            await send_main_menu(callback.message)
            
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка при сохранении!</b>\n\n"
                "Возможно, это дублирующая запись или проблемы с доступом к Google Sheets.\n"
                "Попробуйте еще раз через несколько секунд.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении записи: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при сохранении!</b>\n\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            parse_mode="HTML"
        )


@dp.message(Command("last"))
async def cmd_last_entries(message: Message):
    """Команда для просмотра последних записей"""
    await show_last_entries(message)


@dp.callback_query(F.data == "last_entries")
async def callback_last_entries(callback: CallbackQuery):
    """Callback для просмотра последних записей"""
    await callback.answer()
    await show_last_entries(callback.message, edit_message=True)


async def show_last_entries(message: Message, edit_message: bool = False, limit: int = 5):
    """Показывает последние записи"""
    try:
        last_rows = sheets_client.get_last_rows(limit)
        
        if not last_rows:
            text = "📋 <b>Последние записи</b>\n\nЗаписи не найдены."
        else:
            text = f"📋 <b>Последние {len(last_rows)} записей</b>\n\n"
            
            for i, row in enumerate(last_rows, 1):
                engineer = row.get('engineer', 'Не указан')
                date = row.get('date', '')
                time_start = row.get('time_start', '')
                time_end = row.get('time_end', '')
                distance_km = row.get('distance_km', '0')
                project = row.get('project', '')
                address = row.get('address', '')
                
                text += f"<b>{i}. {engineer}</b>\n"
                text += f"📅 {date} | ⏱️ {time_start}-{time_end}\n"
                text += f"📏 {distance_km} км"
                
                if project:
                    text += f" | 🏗️ {project[:20]}{'...' if len(project) > 20 else ''}"
                
                if address:
                    text += f" | 📍 {address[:20]}{'...' if len(address) > 20 else ''}"
                
                text += "\n\n"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Обновить", callback_data="last_entries")
        keyboard.button(text="🏠 Главное меню", callback_data="main_menu")
        keyboard.adjust(1, 1)
        
        if edit_message:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Ошибка при получении последних записей: {e}")
        error_text = "❌ Ошибка при получении данных из Google Sheets."
        
        if edit_message:
            await message.edit_text(error_text)
        else:
            await message.answer(error_text)


@dp.message(Command("edit_last"))
async def cmd_edit_last(message: Message, state: FSMContext):
    """Команда для редактирования последней записи"""
    await start_edit_last_entry(message, state)


@dp.callback_query(F.data == "edit_last")
async def callback_edit_last(callback: CallbackQuery, state: FSMContext):
    """Callback для редактирования последней записи"""
    await callback.answer()
    await start_edit_last_entry(callback.message, state, edit_message=True)


async def start_edit_last_entry(message: Message, state: FSMContext, edit_message: bool = False):
    """Начинает процесс редактирования последней записи"""
    user_id = message.from_user.id
    
    # Получаем последнюю запись пользователя
    last_entry = sheets_client.get_last_user_entry(user_id)
    
    if not last_entry:
        text = "❌ У вас нет записей для редактирования."
        
        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return
    
    # Проверяем, можно ли еще редактировать (15 минут)
    created_at = last_entry.get('created_at', '')
    if not time_utils.is_within_edit_time_limit(created_at, 15):
        text = (
            "❌ <b>Время редактирования истекло!</b>\n\n"
            "Редактировать записи можно только в течение 15 минут после создания."
        )
        
        if edit_message:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return
    
    # Сохраняем данные записи в состояние
    await state.update_data(edit_entry=last_entry)
    
    # Показываем текущую запись и поля для редактирования
    engineer = last_entry.get('engineer', '')
    date = last_entry.get('date', '')
    time_start = last_entry.get('time_start', '')
    time_end = last_entry.get('time_end', '')
    distance_km = last_entry.get('distance_km', '0')
    project = last_entry.get('project', '')
    address = last_entry.get('address', '')
    comment = last_entry.get('comment', '')
    
    text = (
        f"✏️ <b>Редактирование записи</b>\n\n"
        f"👤 <b>Инженер:</b> {engineer}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"🕐 <b>Время:</b> {time_start} - {time_end}\n"
        f"📏 <b>Пробег:</b> {distance_km} км\n"
        f"🏗️ <b>Проект:</b> {project or '(не указан)'}\n"
        f"📍 <b>Адрес:</b> {address or '(не указан)'}\n"
        f"💬 <b>Комментарий:</b> {comment[:50]}{'...' if len(comment) > 50 else ''}\n\n"
        f"Что хотите изменить?"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🏗️ Проект", callback_data="edit_project")
    keyboard.button(text="📍 Адрес", callback_data="edit_address")
    keyboard.button(text="💬 Комментарий", callback_data="edit_comment")
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    keyboard.adjust(2, 1, 1)
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    
    await state.set_state(EditStates.waiting_field_choice)


@dp.callback_query(F.data.startswith("edit_"), StateFilter(EditStates.waiting_field_choice))
async def handle_edit_field_choice(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора поля для редактирования"""
    await callback.answer()
    
    field = callback.data.replace("edit_", "")
    await state.update_data(edit_field=field)
    
    field_names = {
        "project": "🏗️ Проект",
        "address": "📍 Адрес",
        "comment": "💬 Комментарий"
    }
    
    field_name = field_names.get(field, field)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование поля: {field_name}</b>\n\n"
        f"Введите новое значение:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(EditStates.waiting_new_value)


@dp.message(F.text, StateFilter(EditStates.waiting_new_value))
async def handle_edit_new_value(message: Message, state: FSMContext):
    """Обработчик ввода нового значения поля"""
    data = await state.get_data()
    field = data['edit_field']
    new_value = message.text.strip()
    edit_entry = data['edit_entry']
    
    # Обновляем значение поля
    edit_entry[field] = new_value
    
    # Находим строку в Google Sheets по row_uid
    row_uid = edit_entry.get('row_uid')
    if not row_uid:
        await message.answer("❌ Не удалось найти запись для редактирования.")
        await state.clear()
        return
    
    row_info = sheets_client.find_row_by_uid(row_uid, message.from_user.id)
    
    if not row_info:
        await message.answer("❌ Запись не найдена или у вас нет прав на её редактирование.")
        await state.clear()
        return
    
    row_number, row_data = row_info
    
    # Создаем новый объект TripEntry с обновленными данными
    user = users_repo.get_user(message.from_user.id)
    
    try:
        # Парсим время из sheets
        start_dt = time_utils.parse_sheets_datetime(edit_entry['date'], edit_entry['time_start'])
        end_dt = time_utils.parse_sheets_datetime(edit_entry['date'], edit_entry['time_end'])
        
        if not start_dt or not end_dt:
            await message.answer("❌ Ошибка при обработке времени.")
            await state.clear()
            return
        
        updated_entry = TripEntry(
            date=edit_entry['date'],
            time_start=edit_entry['time_start'],
            time_end=edit_entry['time_end'],
            odometer_start=int(edit_entry['odometer_start']),
            odometer_end=int(edit_entry['odometer_end']),
            distance_km=int(edit_entry['distance_km']),
            engineer=user.full_name,
            project=edit_entry.get('project', ''),
            address=edit_entry.get('address', ''),
            comment=edit_entry.get('comment', ''),
            created_at=edit_entry['created_at'],
            author_tg_id=message.from_user.id,
            row_uid=row_uid
        )
        
        # Обновляем строку в Google Sheets
        success = sheets_client.update_row(row_number, updated_entry)
        
        if success:
            field_names = {
                "project": "🏗️ Проект",
                "address": "📍 Адрес",
                "comment": "💬 Комментарий"
            }
            
            await message.answer(
                f"✅ <b>Запись обновлена!</b>\n\n"
                f"{field_names.get(field, field)} изменен на:\n"
                f"<code>{new_value}</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка при обновлении записи в Google Sheets.")
        
    except Exception as e:
        logger.error(f"Ошибка при редактировании записи: {e}")
        await message.answer("❌ Произошла ошибка при редактировании записи.")
    
    await state.clear()


@dp.message(Command("export"))
async def cmd_export(message: Message):
    """Команда экспорта (только для админов)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await show_export_info(message)


@dp.callback_query(F.data == "export")
async def callback_export(callback: CallbackQuery):
    """Callback экспорта"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await callback.answer()
    await show_export_info(callback.message, edit_message=True)


async def show_export_info(message: Message, edit_message: bool = False):
    """Показывает информацию об экспорте"""
    try:
        # Получаем статистику
        last_rows = sheets_client.get_last_rows(10)
        total_users = users_repo.get_all_users_count()
        
        # Создаем ссылку на таблицу
        sheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEET_ID')}/edit"
        
        text = (
            f"👑 <b>Панель администратора</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"👥 Зарегистрированных пользователей: {total_users}\n"
            f"📝 Записей в таблице: {len(last_rows)}\n\n"
            f"🔗 <a href='{sheet_url}'>Открыть Google Sheets</a>\n\n"
            f"<i>Последние записи отображены в разделе 'Последние записи'</i>"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📋 Последние записи", callback_data="last_entries")
        keyboard.button(text="🏠 Главное меню", callback_data="main_menu")
        keyboard.adjust(1, 1)
        
        if edit_message:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Ошибка при показе экспорта: {e}")
        error_text = "❌ Ошибка при получении данных."
        
        if edit_message:
            await message.edit_text(error_text)
        else:
            await message.answer(error_text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    await show_help(message)


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Callback помощи"""
    await callback.answer()
    await show_help(callback.message, edit_message=True)


async def show_help(message: Message, edit_message: bool = False):
    """Показывает справку"""
    help_text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Регистрация и главное меню\n"
        "/new - Создать новую запись поездки\n"
        "/last - Показать последние записи\n"
        "/edit_last - Редактировать последнюю запись\n"
        "/help - Показать эту справку\n\n"
        "<b>Создание записи:</b>\n"
        "1. Время начала (сейчас/ручной ввод)\n"
        "2. Показания одометра начала\n"
        "3. Время окончания\n"
        "4. Показания одометра окончания\n"
        "5. Проект (необязательно)\n"
        "6. Адрес (необязательно)\n"
        "7. Комментарий\n"
        "8. Подтверждение и сохранение\n\n"
        "<b>Форматы времени:</b>\n"
        "• <code>сейчас</code> - текущее время\n"
        "• <code>14:30</code> - время сегодня\n"
        "• <code>21.09.2024 14:30</code> - полная дата\n\n"
        "<b>Редактирование:</b>\n"
        "Можно редактировать проект, адрес и комментарий в течение 15 минут после создания записи."
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🏠 Главное меню", callback_data="main_menu")
    
    if edit_message:
        await message.edit_text(help_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(help_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


# Обработчики для навигации
@dp.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await asyncio.sleep(1)
    await send_main_menu(callback.message)


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("🏠 Главное меню")
    await send_main_menu(callback.message)


@dp.callback_query(F.data == "go_back")
async def callback_go_back(callback: CallbackQuery, state: FSMContext):
    """Кнопка "Назад" в подтверждении"""
    await callback.answer()
    await callback.message.edit_text("🔙 Возвращение к редактированию...")
    await ask_comment(callback.message, state, edit_message=True)


# Запуск бота
async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск Telegram-бота...")
    
    # Проверяем наличие необходимых файлов и переменных
    required_env_vars = ["TELEGRAM_APITOKEN", "GOOGLE_SHEET_ID"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        return
    
    service_account_path = os.getenv("GOOGLE_SA_JSON_PATH", "./service_account.json")
    if not os.path.exists(service_account_path):
        logger.error(f"Файл сервисного аккаунта не найден: {service_account_path}")
        return
    
    logger.info("Все проверки пройдены, запускаем polling...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
