# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# وارد کردن کلاس‌ها و توابع از فایل‌های دیگر پروژه
from . import models
from .database import SessionLocal, engine
from .chatbot import FitnessCoachAssistant

# این دستور، اگر جداول وجود نداشته باشند، آن‌ها را می‌سازد
# (جایگزین بهتری برای اسکریپت create_db.py در محیط پروداکشن)
models.Base.metadata.create_all(bind=engine)

# ساخت اپلیکیشن FastAPI
app = FastAPI(title="Fit Coach AI API")

# --- مدیریت حافظه چت برای هر کاربر ---
# یک دیکشنری ساده برای نگهداری یک نمونه از دستیار برای هر کاربر
# نکته: در یک اپلیکیشن واقعی و بزرگ، از راه حل بهتری مثل Redis استفاده می‌شود
chat_sessions = {}

# --- مدل‌های Pydantic برای اعتبارسنجی ورودی و خروجی API ---
class ChatRequest(BaseModel):
    telegram_user_id: int
    message: str
    first_name: str | None = None # اختیاری، برای ساخت کاربر جدید

class ChatResponse(BaseModel):
    ai_response: str
    is_final: bool = False
    plan_data: dict | None = None

# --- Dependency برای مدیریت Session دیتابیس ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- تعریف API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    این Endpoint اصلی برای مدیریت گفتگوی کاربر است.
    """
    # ۱. پیدا کردن یا ساختن کاربر در دیتابیس
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    if not user:
        user = models.User(
            telegram_user_id=request.telegram_user_id,
            first_name=request.first_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # ۲. پیدا کردن یا ساختن یک جلسه چت (Chat Session) برای کاربر
    if user.telegram_user_id not in chat_sessions:
        chat_sessions[user.telegram_user_id] = FitnessCoachAssistant()
    
    assistant = chat_sessions[user.telegram_user_id]

    # ۳. ذخیره پیام کاربر در تاریخچه
    user_chat = models.ChatHistory(user_id=user.id, sender="user", message_text=request.message)
    db.add(user_chat)
    db.commit()

    # ۴. گرفتن پاسخ از هوش مصنوعی
    ai_message_text = assistant.get_response(request.message)

    # ۵. ذخیره پیام AI در تاریخچه
    ai_chat = models.ChatHistory(user_id=user.id, sender="ai", message_text=ai_message_text)
    db.add(ai_chat)
    db.commit()

    # ۶. بررسی اینکه آیا مکالمه تمام شده و باید برنامه ساخته شود
    plan_params = assistant.parse_final_response(ai_message_text)
    if plan_params:
        # TODO: در قدم بعدی، اینجا منطق ساخت برنامه تمرینی را اضافه می‌کنیم
        print(f"Plan parameters extracted for user {user.telegram_user_id}: {plan_params}")
        
        # پاک کردن جلسه چت بعد از اتمام کار
        del chat_sessions[user.telegram_user_id]
        
        return ChatResponse(
            ai_response="برنامه شما در حال آماده شدن است...",
            is_final=True,
            plan_data=plan_params
        )

    return ChatResponse(ai_response=ai_message_text)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fit Coach AI API!"}