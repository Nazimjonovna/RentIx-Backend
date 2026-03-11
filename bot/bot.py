import asyncio
import os
import ssl
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher

# Relative import
from .handlers import router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔹 Windows SSL fix (development / test uchun)
ssl._create_default_https_context = ssl._create_unverified_context

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("✅ Bot ishga tushdi")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())