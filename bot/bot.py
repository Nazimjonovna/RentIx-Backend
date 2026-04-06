import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import httpx

logging.basicConfig(level=logging.INFO)

BOT_TOKEN  = "7820267802:AAG5u8tLtQzXFPhOomI8LLwEe8it0Z3BrXI"
API_BASE   = "https://167.172.76.94"
WEBAPP_URL = "https://user.mirabbosoff.uz"

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


async def api_post(endpoint: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        try:
            r = await client.post(f"{API_BASE}{endpoint}", json=data)
            return r.json()
        except Exception as e:
            logging.error(f"API xatolik: {e}")
            return {"status": False, "detail": "Server bilan bog'lanishda xatolik"}


def webapp_keyboard(token: str = "") -> InlineKeyboardMarkup:
    url = f"{WEBAPP_URL}?token={token}" if token else WEBAPP_URL
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Ilovani ochish",
            web_app=WebAppInfo(url=url)
        )
    ]])


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = str(message.from_user.id)

    result = await api_post("/api/token/", {"telegram_id": telegram_id})

    if result.get("status"):
        # Foydalanuvchi topildi → token bilan frontga
        user   = result["user"]
        access = result["tokens"]["access"]

        await message.answer(
            f"Xush kelibsiz, {user['full_name']}!\n\n"
            "Ilovani ochish uchun quyidagi tugmani bosing:",
            reply_markup=webapp_keyboard(access)
        )
    else:
        # Foydalanuvchi topilmadi → token siz frontga (u yerda register qiladi)
        await message.answer(
            "Ilovani ochish uchun quyidagi tugmani bosing:",
            reply_markup=webapp_keyboard()
        )


async def main():
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())