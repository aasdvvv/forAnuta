import logging
import asyncio
import requests
import pdfplumber
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# КОНФИГУРАЦИЯ
BOT_TOKEN = "8836621651:AAGssQCktlD8IEJp5Tb1CaiVOce98zjjkfc"  # Вставьте сюда ваш токен от BotFather полностью
PDF_URL = "https://for-anuta.vercel.app/api"
SYSTEM_PROXY = "http://proxy.server:3128"

# Настройка сессии aiogram с прокси для доступа к Telegram API
session = AiohttpSession(proxy=SYSTEM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

def download_and_parse_pdf():
    """Скачивает PDF через Vercel прокси с использованием системного прокси PythonAnywhere."""
    try:
        proxies = {
            "http": SYSTEM_PROXY,
            "https": SYSTEM_PROXY
        }
        response = requests.get(PDF_URL, proxies=proxies, timeout=15)
        response.raise_for_status()
        
        with open("timetable.pdf", "wb") as f:
            f.write(response.content)
            
        logging.info("PDF успешно загружен через Vercel.")
        
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
    await message.answer("Привет! Я бот мониторинга расписания. Нажми /check для проверки.")

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("Запрашиваю расписание...")
    parsed_data = download_and_parse_pdf()
    if parsed_data:
        await message.answer(f"Расписание получено:\n\n{parsed_data}")
    else:
        await message.answer("Не удалось загрузить расписание.")

async def check_schedule_updates():
    logging.info("Автоматическая проверка расписания...")

async def main():
    scheduler.add_job(check_schedule_updates, 'interval', hours=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
