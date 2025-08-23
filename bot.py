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

async def get_user_status(user_id: int) -> dict:
    """وضعیت کاربر (آیا فرم را پر کرده؟) را از بک‌اند می‌پرسد."""
    try:
        response = requests.get(f"{API_BASE_URL}/users/status/{user_id}", timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get status for user {user_id}. Error: {e}")
        return {"form_completed": False, "plan_generated": False} # مقدار پیش‌فرض در صورت خطا

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    کاربر را ثبت‌نام کرده و سپس دکمه وب‌اپ را نمایش می‌دهد.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")
    
    # --- بخش کلیدی جدید: ثبت‌نام فوری کاربر ---
    try:
        register_payload = {
            "telegram_user_id": user.id,
            "first_name": user.first_name
        }
        response = requests.post(f"{API_BASE_URL}/register", json=register_payload, timeout=10)
        response.raise_for_status() # بررسی خطاهای احتمالی سرور
        logger.info(f"User {user.id} registered or already exists.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to register user {user.id}. Error: {e}")
        await update.message.reply_text("متاسفانه در حال حاضر مشکلی در اتصال به سرور وجود دارد. لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
        return # اجرای تابع متوقف می‌شود
    # --- پایان بخش ثبت‌نام ---

    # پس از ثبت‌نام موفق، دکمه را نمایش می‌دهیم
    status = await get_user_status(user.id)
    
    params = {
        "user_id": user.id,
        "first_name": urllib.parse.quote(user.first_name or "کاربر")
    }
    if status.get("form_completed"):
        params["skip_form"] = "true"
    if status.get("plan_generated"):
        params["show_plan"] = "true"

    web_app_url_with_params = f"{BASE_WEB_APP_URL}?{urllib.parse.urlencode(params)}"

    keyboard = [[InlineKeyboardButton("🚀 باز کردن دستیار هوشمند", web_app=WebAppInfo(url=web_app_url_with_params))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = f"سلام {user.first_name} عزیز! برای ادامه روی دکمه زیر کلیک کن."
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
