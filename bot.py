# bot.py
import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
import urllib.parse

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "1991464642:AAG_1PuUDkcIw8otMoBJ3I-_41bD7974YsY")
BASE_WEB_APP_URL = "https://fitcoachapp-mhz8neos3buegdphlxfqzb.streamlit.app/"
API_BASE_URL = "https://fitcoachapp-production.up.railway.app"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")
    
    try:
        register_payload = {"telegram_user_id": user.id, "first_name": user.first_name}
        response = requests.post(f"{API_BASE_URL}/register", json=register_payload, timeout=10)
        response.raise_for_status()
        logger.info(f"User {user.id} registered or already exists.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to register user {user.id}. Error: {e}")
        await update.message.reply_text("متاسفانه در حال حاضر مشکلی در اتصال به سرور وجود دارد. لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
        return

    params = {
        "user_id": user.id,
        "first_name": urllib.parse.quote(user.first_name or "کاربر")
    }
    web_app_url_with_params = f"{BASE_WEB_APP_URL}?{urllib.parse.urlencode(params)}"
    keyboard = [[InlineKeyboardButton("🚀 باز کردن فرم مشخصات", web_app=WebAppInfo(url=web_app_url_with_params))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = f"سلام {user.first_name} عزیز! برای شروع و طراحی برنامه شخصی‌سازی شده، روی دکمه زیر کلیک کن."
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()