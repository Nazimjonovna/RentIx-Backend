import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")  # Misol: http://127.0.0.1:8000

def get_user(telegram_id: int, phone: str = None):
    """
    Foydalanuvchi token olish uchun API ga POST qiladi.
    Telegram ID yoki Phone bo'lishi yetarli.
    """
    if not telegram_id and not phone:
        print("Telegram ID yoki Phone majburiy!")
        return None

    url = f"{API_URL}/user/token/"
    payload = {}

    if telegram_id:
        payload["telegram_id"] = telegram_id
    if phone:
        payload["phone"] = phone

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"API response code: {r.status_code}, message: {r.text}")
            return None
    except requests.RequestException as e:
        print("Get user error:", e)
        return None


def login_api(login: str, password: str):
    """
    Admin yoki manager login qilish uchun API ga POST qiladi.
    """
    if not login or not password:
        print("Login va Password majburiy!")
        return None

    url = f"{API_URL}/login/"
    payload = {
        "login": login,
        "password": password
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Login API response code: {r.status_code}, message: {r.text}")
            return None
    except requests.RequestException as e:
        print("Login error:", e)
        return None