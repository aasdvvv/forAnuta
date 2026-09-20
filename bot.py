print(">>> СКРИПТ НАЧАЛ ВЫПОЛНЕНИЕ...", flush=True)

import logging
import asyncio
import aiohttp
import pdfplumber
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
PDF_URL = "https://for-anuta.vercel.app/api"
SYSTEM_PROXY = "http://proxy.server:3128"

session = AiohttpSession(proxy=SYSTEM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# 1. СНАЧАЛА ОБЪЯВЛЯЕМ ФУНКЦИЮ СКАЧИВАНИЯ И ПАРСИНГА
async def download_and_parse_pdf():
    """Скачивает PDF с расписанием через Vercel прокси с заголовками Chrome."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as client:
            async with client.get(PDF_URL, proxy=SYSTEM_PROXY, timeout=20) as resp:
                if resp.status != 200:
                    logging.error(f"Ошибка ответа Vercel: статус {resp.status}")
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

# 2. ЗАТЕМ ОБЪЯВЛЯЕМ ХЭНДЛЕРЫ
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

# 3. ТОЧКА ВХОДА
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook успешно сброшен. Запускаем polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
