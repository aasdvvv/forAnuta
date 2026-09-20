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
BOT_TOKEN = "8836621651:AAGssQCktlD8IEJp5Tb1CaiVOce98zjjkfc"  # Укажите ваш токен от BotFather полностью
PDF_URL = "https://for-anuta.vercel.app/api"
SYSTEM_PROXY = "http://proxy.server:3128"

# Сессия Telegram идет через прокси PythonAnywhere
session = AiohttpSession(proxy=SYSTEM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

async def download_and_parse_pdf():
    """Скачивает PDF асинхронно напрямую через aiohttp."""
    try:
        # Прямой асинхронный запрос к Vercel
        async with aiohttp.ClientSession() as client:
            async with client.get(PDF_URL, timeout=15) as resp:
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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
