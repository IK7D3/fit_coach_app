# bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# --- تنظیمات اولیه ---
# توکن ربات خود را اینجا قرار دهید. بهتر است از متغیرهای محیطی استفاده کنید.
TELEGRAM_BOT_TOKEN = "1991464642:AAG_1PuUDkcIw8otMoBJ3I-_41bD7974YsY"

# آدرس وب‌اپ استریم‌لیت شما (بعد از استقرار، این آدرس را جایگزین کنید)
WEB_APP_URL = "https://fitcoachapp-mhz8neos3buegdphlxfqzb.streamlit.app/" 

# فعال کردن لاگ برای خطایابی بهتر
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
    
    # ساخت دکمه برای باز کردن وب‌اپ
    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 باز کردن دستیار هوشمند",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ارسال پیام خوشامدگویی به همراه دکمه
    welcome_message = (
        f"سلام {user.first_name} عزیز!\n\n"
        "به دستیار هوشمند مربی خوش آمدی. برای شروع مصاحبه و دریافت برنامه تمرینی رایگان، "
        "لطفاً روی دکمه زیر کلیک کن."
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# --- راه‌اندازی و اجرای ربات ---

def main() -> None:
    """ربات را راه‌اندازی و اجرا می‌کند."""
    
    # خواندن توکن از متغیرهای محیطی برای امنیت بیشتر
    token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    if not token:
        raise ValueError("توکن ربات تلگرام یافت نشد. لطفاً آن را تنظیم کنید.")

    # ساخت اپلیکیشن ربات
    application = Application.builder().token(token).build()

    # ثبت دستور /start
    application.add_handler(CommandHandler("start", start))

    # اجرای ربات تا زمانی که کاربر آن را متوقف کند
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()