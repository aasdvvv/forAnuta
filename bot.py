import logging
import asyncio
import aiohttp
import pdfplumber
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

# КОНФИГУРАЦИЯ
BOT_TOKEN = "8836621651:AAEscTZES2lxYCsUZWukmZ7pKYd2JHABSN4"  # Укажите токен от BotFather
PDF_URL = "https://for-anuta.vercel.app/api"
SYSTEM_PROXY = "http://proxy.server:3128"

# Стандартная HTTP-сессия aiogram с поддержкой системного прокси PythonAnywhere
session = AiohttpSession(proxy=SYSTEM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

async def download_and_parse_pdf():
    """Скачивает PDF через Vercel прокси."""
    try:
        # Для запроса к Vercel прокси PythonAnywhere указывается через параметр proxy
        async with aiohttp.ClientSession() as client:
            async with client.get(PDF_URL, proxy=SYSTEM_PROXY, timeout=15) as resp:
                if resp.status != 200:
                    logging.error(f"Ошибка Vercel: статус {resp.status}")
                    return None
                data = await resp.read()

        with open("timetable.pdf", "wb") as f:
            f.write(data)

        logging.info("PDF успешно скачан!")

        text = ""
        with pdfplumber.open("timetable.pdf") as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        return text[:1000] if text else "Текст в PDF не найден."

    except Exception as e:
        logging.error(f"Ошибка при загрузке/парсинге PDF: {e}")
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот расписания. Напиши /check для проверки.")

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("Запрашиваю расписание...")
    parsed_data = await download_and_parse_pdf()
    if parsed_data:
        await message.answer(f"Расписание получено:\n\n{parsed_data}")
    else:
        await message.answer("Не удалось загрузить расписание.")

async def main():
    # Удаляем чужой вебхук и сбрасываем накопленные сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг
    await dp.start_polling(bot)
