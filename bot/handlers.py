from aiogram import Router, types
from aiogram.filters import CommandStart
from .api import get_user, login_api

router = Router()

@router.message(CommandStart())
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    print(message.from_user)
    phone = None  # telefon avtomatik olinmaydi

    # API ga yuborish
    a = (telegram_id, phone)
    user_data = get_user(telegram_id, phone)

    if not user_data or not user_data.get("status"):
        await message.answer(f"Foydalanuvchi topilmadi ❌\n{user_data}\n{a}")
        return

    role = user_data["user"]["role"]

    if role == "user":
        await message.answer("Foydalanuvchi topildi ✅")
    elif role in ["admin", "manager"]:
        await message.answer(f"Siz {role.upper()} sifatida tizimga kirdingiz ✅")
        