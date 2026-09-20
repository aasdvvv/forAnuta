import asyncio
import hashlib
import logging
import os
from io import BytesIO

import pdfplumber
import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Токен вашего бота от @BotFather
BOT_TOKEN = "8836621651:AAGssQCktlD8IEJp5Tb1CaiVOce98zjjkfc"
# Прямая ссылка на PDF-файл расписания на сайте вуза
PDF_URL = "https://fir.bsu.by/images/timetable/ILOG_timetable.pdf"
# Интервал проверки обновлений в минутах
CHECK_INTERVAL_MINUTES = 30

# Настройки прокси PythonAnywhere
PROXY_URL = "http://proxy.server:3128"
proxies = {
    "http": PROXY_URL,
    "https": PROXY_URL,
}

# Временное хранилище расписания в памяти
schedule_data = {}
last_pdf_hash = ""
subscribed_users = set()

# Инициализируем бота с использованием прокси PythonAnywhere
session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()


# --- 1. Функция скачивания и парсинга PDF ---
def fetch_and_parse_pdf():
    global schedule_data, last_pdf_hash

    try:
        # Передаем прокси в requests для скачивания файла
        response = requests.get(PDF_URL, proxies=proxies, timeout=15)
        response.raise_for_status()
        pdf_bytes = response.content

        # Вычисляем MD5-хэш файла для проверки изменений
        current_hash = hashlib.md5(pdf_bytes).hexdigest()

        # Если файл не изменился, повторный парсинг не нужен
        if current_hash == last_pdf_hash and schedule_data:
            return False

        parsed_schedule = {}

        # Открываем PDF из памяти
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        cleaned_row = [
                            cell.strip() if cell else "" for cell in row
                        ]
                        if len(cleaned_row) >= 2:
                            day_or_info = cleaned_row[0]
                            subject_info = " | ".join(cleaned_row[1:])

                            if day_or_info:
                                if day_or_info not in parsed_schedule:
                                    parsed_schedule[day_or_info] = []
                                parsed_schedule[day_or_info].append(
                                    subject_info
                                )

        # Форматируем расписание в удобные текстовые блоки
        formatted_schedule = {}
        for day, items in parsed_schedule.items():
            formatted_schedule[day] = f"📅 **{day}**\n\n" + "\n".join(items)

        if formatted_schedule:
            schedule_data = formatted_schedule
            last_pdf_hash = current_hash
            return True

    except Exception as e:
        logging.error(f"Ошибка при загрузке/парсинге PDF: {e}")

    return False


# --- 2. Периодическая проверка обновлений ---
async def check_schedule_updates():
    is_updated = await asyncio.to_thread(fetch_and_parse_pdf)
    if is_updated and subscribed_users:
        for chat_id in subscribed_users:
            try:
                await bot.send_message(
                    chat_id,
                    "🔔 **Внимание!** Расписание на сайте обновилось. Нажмите /start, чтобы посмотреть свежее.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logging.error(
                    f"Не удалось отправить уведомление {chat_id}: {e}"
                )


# --- 3. Клавиатура и хэндлеры бота ---
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Показать дни", callback_data="list_days"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить обновление вручную",
                    callback_data="refresh",
                )
            ],
        ]
    )
    return keyboard


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    subscribed_users.add(message.chat.id)
    await message.answer(
        "Привет! Я бот с расписанием.\n\n"
        "Я слежу за изменениями PDF-файла на сайте и пришлю уведомление, если расписание обновится.",
        reply_markup=get_main_keyboard(),
    )


@dp.callback_query(F.data == "list_days")
async def process_list_days(callback: types.CallbackQuery):
    if not schedule_data:
        await callback.message.answer(
            "Расписание пока не загружено. Нажмите обновить."
        )
        await callback.answer()
        return

    buttons = []
    for day in schedule_data.keys():
        buttons.append(
            [InlineKeyboardButton(text=day, callback_data=f"day_{day}")]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите день недели:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("day_"))
async def process_day_select(callback: types.CallbackQuery):
    day_name = callback.data.split("day_")[1]
    day_schedule = schedule_data.get(day_name, "Данные не найдены.")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к дням", callback_data="list_days"
                )
            ]
        ]
    )
    await callback.message.edit_text(
        day_schedule, parse_mode="Markdown", reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data == "refresh")
async def process_refresh(callback: types.CallbackQuery):
    await callback.answer("Проверяем файл на сайте...")
    updated = await asyncio.to_thread(fetch_and_parse_pdf)
    if updated:
        await callback.message.answer("✅ Найдено и загружено новое расписание!")
    else:
        await callback.message.answer("ℹ️ Расписание актуально, изменений нет.")


# --- 4. Запуск бота и планировщика ---
async def main():
    logging.basicConfig(level=logging.INFO)

    # Загружаем расписание при старте
    await asyncio.to_thread(fetch_and_parse_pdf)

    # Настраиваем фоновую проверку PDF
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_schedule_updates, "interval", minutes=CHECK_INTERVAL_MINUTES
    )
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())