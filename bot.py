# bot.py
import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
import urllib.parse

# --- تنظیمات اولیه ---
TELEGRAM_BOT_TOKEN = "1991464642:AAG_1PuUDkcIw8otMoBJ3I-_41bD7974YsY"
BASE_WEB_APP_URL = "https://fitcoachapp-mhz8neos3buegdphlxfqzb.streamlit.app/" # آدرس اصلی استریم‌لیت
API_BASE_URL = "https://fitcoachapp-production.up.railway.app"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- تعریف دستورات ربات ---

async def register_user(user_id: int, first_name: str):
    """در پشت صحنه، کاربر را در سیستم ما ثبت‌نام می‌کند."""
    try:
        payload = {"telegram_user_id": user_id, "first_name": first_name}
        response = requests.post(f"{API_BASE_URL}/register", json=payload)
        response.raise_for_status()
        logger.info(f"User {user_id} registered successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to register user {user_id}. Error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    این تابع زمانی اجرا می‌شود که کاربر دستور /start را ارسال کند.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")
    
    # قدم ۱: ثبت‌نام کاربر در بک‌اند
    registration_successful = await register_user(user.id, user.first_name or "کاربر")

    if not registration_successful:
        await update.message.reply_text("متاسفانه در حال حاضر مشکلی در سیستم وجود دارد. لطفاً کمی بعد دوباره تلاش کنید.")
        return

    # قدم ۲: ساخت دکمه و ارسال پیام
    encoded_first_name = urllib.parse.quote(user.first_name or "کاربر")
    web_app_url_with_params = f"{BASE_WEB_APP_URL}?user_id={user.id}&first_name={encoded_first_name}"

    keyboard = [[InlineKeyboardButton("🚀 باز کردن دستیار هوشمند", web_app=WebAppInfo(url=web_app_url_with_params))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        f"سلام {user.first_name} عزیز!\n\n"
        "ثبت‌نام شما با موفقیت انجام شد. برای شروع مصاحبه و دریافت برنامه، روی دکمه زیر کلیک کن."
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# --- راه‌اندازی و اجرای ربات ---

def main() -> None:
    """ربات را راه‌اندازی و اجرا می‌کند."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    if not token:
        raise ValueError("توکن ربات تلگرام یافت نشد. لطفاً آن را تنظیم کنید.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
