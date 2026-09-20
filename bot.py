print(">>> СКРИПТ НАЧАЛ ВЫПОЛНЕНИЕ...", flush=True)
import logging
import asyncio
import aiohttp
import pdfplumber
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession

# Включаем логирование, чтобы видеть все действия бота в консоли
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8836621651:AAEscTZES2lxYCsUZWukmZ7pKYd2JHABSN4"  # Токен от @BotFather
PDF_URL = "https://for-anuta.vercel.app/api"
SYSTEM_PROXY = "http://proxy.server:3128"

# Настройка сессии aiogram через системный HTTP-прокси PythonAnywhere
session = AiohttpSession(proxy=SYSTEM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

async def download_and_parse_pdf():
    """Скачивает PDF с расписанием через Vercel прокси и извлекает текст."""
    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(PDF_URL, proxy=SYSTEM_PROXY, timeout=15) as resp:
                if resp.status != 200:
                    logging.error(f"Ошибка Vercel: статус {resp.status}")
                    return None
                data = await resp.read()

        with open("timetable.pdf", "wb") as f:
            f.write(data)

        text = ""
        with pdfplumber.open("timetable.pdf") as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

        return text[:1000] if text else "Текст в PDF не найден."

    except Exception as e:
        logging.error(f"Ошибка при загрузке/парсинге PDF: {e}")
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот расписания ФМО. Напиши /check, чтобы получить актуальное расписание.")

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("Запрашиваю расписание, подождите...")
    parsed_data = await download_and_parse_pdf()
    if parsed_data:
        await message.answer(f"**Расписание:**\n\n{parsed_data}")
    else:
        await message.answer("Не удалось загрузить или разобрать расписание.")

async def main():
    # 1. Принудительно сносим старый Webhook, который мог остаться от сторонних сервисов
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook успешно сброшен. Запускаем polling...")
    
    # 2. Запускаем получение обновлений
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
