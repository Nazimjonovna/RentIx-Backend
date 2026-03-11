# main.py
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# .env fayldan tokenni olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylda kiritilmagan!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# /start tugmasi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    tg_id = message.from_user.id
    nickname = message.from_user.username or message.from_user.full_name

    # Telegram foydalanuvchisi profilida faqat ID va nickname mavjud
    await message.answer(
        f"Salom!\nTelegram ID: {tg_id}\nNickname: {nickname}"
    )

# Botni ishga tushirish
async def main():
    print("✅ Bot ishga tushdi")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())