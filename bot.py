# bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
import urllib.parse

# --- تنظیمات اولیه ---
TELEGRAM_BOT_TOKEN = "1991464642:AAG_1PuUDkcIw8otMoBJ3I-_41bD7974YsY"
BASE_WEB_APP_URL = "https://your-streamlit-app-url.streamlit.app" # آدرس اصلی استریم‌لیت

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- تعریف دستورات ربات ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    این تابع زمانی اجرا می‌شود که کاربر دستور /start را ارسال کند.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")
    
    # ساخت URL داینامیک با اطلاعات کاربر
    # ما نام کاربر را URL-encode می‌کنیم تا کاراکترهای خاص مثل فاصله مشکلی ایجاد نکنند
    encoded_first_name = urllib.parse.quote(user.first_name or "کاربر")
    web_app_url_with_params = f"{BASE_WEB_APP_URL}?user_id={user.id}&first_name={encoded_first_name}"

    # ساخت دکمه برای باز کردن وب‌اپ
    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 باز کردن دستیار هوشمند",
                web_app=WebAppInfo(url=web_app_url_with_params)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ارسال پیام خوشامدگویی به همراه دکمه
    welcome_message = (
        f"سلام {user.first_name} عزیز!\n\n"
        "به دستیار هوشمند مربی خوش آمدی. برای شروع مصاحبه و دریافت برنامه تمرینی رایگان, "
        "لطفاً روی دکمه زیر کلیک کن."
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
