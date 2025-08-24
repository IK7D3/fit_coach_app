# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from sqlalchemy import text 
# وارد کردن کلاس‌ها و توابع از فایل‌های دیگر پروژه
from . import models
from .database import SessionLocal, engine
from .chatbot import FitnessCoachAssistant, SYSTEM_PROMPT

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fit Coach AI API")

chat_sessions = {}

# --- مدل‌های Pydantic ---
class UserDataForm(BaseModel):
    telegram_user_id: int
    gender: str
    height_cm: float
    current_weight_kg: float
    target_weight_kg: float

class RegisterRequest(BaseModel):
    telegram_user_id: int
    first_name: str | None = None

class ChatRequest(BaseModel):
    telegram_user_id: int
    message: str
    first_name: str | None = None

class ChatResponse(BaseModel):
    ai_response: str
    is_final: bool = False
    plan_data: dict | None = None

class ChatHistoryResponse(BaseModel):
    sender: str
    message_text: str

class UserStatusResponse(BaseModel):
    form_completed: bool
    plan_generated: bool

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---

@app.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    کاربر را فقط در صورت عدم وجود، در دیتابیس ثبت‌نام می‌کند.
    این تابع دیگر مسئول شروع گفتگو نیست.
    """
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    
    # اگر کاربر وجود نداشت، آن را می‌سازیم
    if not user:
        user = models.User(
            telegram_user_id=request.telegram_user_id, 
            first_name=request.first_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"status": "success", "message": "User created successfully."}

    return {"status": "success", "message": "User already exists."}

@app.post("/users/form-data")
def update_user_form_data(form_data: UserDataForm, db: Session = Depends(get_db)):
    """اطلاعات فرم کاربر را دریافت و در دیتابیس ذخیره می‌کند."""
    user = db.query(models.User).filter(models.User.telegram_user_id == form_data.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.gender = form_data.gender
    user.height_cm = form_data.height_cm
    user.current_weight_kg = form_data.current_weight_kg
    user.target_weight_kg = form_data.target_weight_kg
    
    db.commit()
    return {"status": "success", "message": "User data updated successfully."}

@app.get("/users/status/{telegram_user_id}", response_model=UserStatusResponse)
def get_user_status(telegram_user_id: int, db: Session = Depends(get_db)):
    """بررسی می‌کند آیا کاربر فرم را پر کرده و آیا برنامه‌ای برایش ساخته شده است."""
    user = db.query(models.User).filter(models.User.telegram_user_id == telegram_user_id).first()
    if not user:
        return UserStatusResponse(form_completed=False, plan_generated=False)
    
    form_completed = all([user.gender, user.height_cm, user.current_weight_kg, user.target_weight_kg])
    plan_exists = db.query(models.GeneratedPlan).filter(models.GeneratedPlan.user_id == user.id).first() is not None
    
    return UserStatusResponse(form_completed=form_completed, plan_generated=plan_exists)

DIALOGUE_QUESTIONS = [
    # step 1
    "اول از همه، درصد چربی و درصد تقریبی عضلات بدنت رو می‌دونی؟ اگر نمی‌دونی، فقط بهم بگو بدنت به کدوم توصیف نزدیک‌تره: الف) عضلانی و خشک، ب) عضلانی با کمی چربی، ج) بیشتر اضافه وزن دارم.",
    # step 2
    "بسیار خب. حالا بهم بگو آیا ناهنجاری اسکلتی مثل دیسک کمر، گودی کمر شدید، قوز پشتی یا درد مزمن در مفاصلت داری؟",
    # step 3
    "ممنون. وقتی به بدنت در آینه نگاه می‌کنی، اولین تغییر مثبتی که دوست داری ببینی چی هست؟ (مثلا شکم صاف‌تر، بازوهای حجیم‌تر، یا فرم بهتر پاها)",
    # step 4
    "درک می‌کنم. رسیدن به این هدف، چه فرصت‌های جدیدی رو در زندگی شخصی یا شغلی برات باز می‌کنه؟",
    # step 5
    "عالیه. حالا بریم سراغ برنامه‌ریزی. در هفته چند روز می‌تونی با تمرکز کامل برای تمرین وقت بذاری؟",
    # step 6
    "و سوال آخر: آیا حرکت یا تمرین خاصی وجود داره که از انجام دادنش می‌ترسی یا حس می‌کنی بهت آسیب می‌زنه؟ (مثلاً بعضی‌ها با حرکت اسکات یا ددلیفت راحت نیستند)"
]

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ذخیره پیام کاربر در تاریخچه
    user_chat = models.ChatHistory(user_id=user.id, sender="user", message_text=request.message)
    db.add(user_chat)
    db.commit()

    current_step = user.dialogue_step
    ai_response = ""
    should_increment_step = False

    if current_step >= len(DIALOGUE_QUESTIONS):
        ai_response = "ما تمام سوالات لازم را بررسی کردیم. در حال آماده‌سازی برنامه شما هستیم!"
        # اینجا بعداً منطق ساخت JSON نهایی را اضافه خواهید کرد
    else:
        # --- منطق نگهبان هوش مصنوعی ---
        if current_step == 0:
            # برای پیام اول، همیشه به مرحله بعد می‌رویم
            user_info = (
                f"- جنسیت: {user.gender}\n"
                f"- قد: {user.height_cm} سانتی‌متر\n"
                f"- وزن فعلی: {user.current_weight_kg} کیلوگرم\n"
                f"- وزن هدف: {user.target_weight_kg} کیلوگرم"
            )
            task_prompt = (
                f"این اولین پیام به کاربر است. نام او '{user.first_name}' است. با نامش به او سلام کن و مشخصاتش را به این شکل نمایش بده:\n{user_info}\n"
                f"سپس، این سوال را به شکلی طبیعی و دوستانه از او بپرس: '{DIALOGUE_QUESTIONS[current_step]}'"
            )
            should_increment_step = True
        else:
            # برای سوالات بعدی، پاسخ کاربر را ارزیابی می‌کنیم
            last_user_answer = request.message
            previous_question = DIALOGUE_QUESTIONS[current_step - 1]
            next_question = DIALOGUE_QUESTIONS[current_step]
            task_prompt = (
                f"سوال قبلی که از کاربر پرسیدی این بود: '{previous_question}'. پاسخ اخیر کاربر این است: '{last_user_answer}'.\n"
                f"وظیفه تو: ابتدا پاسخ کاربر را ارزیابی کن.\n"
                f"اگر پاسخ کاربر، جوابی مرتبط به سوال قبلی بود، پاسخت را با تگ [PROCEED] شروع کن، یک جمله کوتاه مثبت بگو و سپس سوال بعدی یعنی این سوال را بپرس: '{next_question}'.\n"
                f"اگر پاسخ کاربر نامرتبط یا بی‌معنی بود، پاسخت را با تگ [REPEAT] شروع کن، با احترام به او بگو روی موضوع متمرکز بماند و همان سوال قبلی یعنی '{previous_question}' را دوباره از او بپرس."
            )

        assistant = chat_sessions.get(user.telegram_user_id, FitnessCoachAssistant())
        chat_sessions[user.telegram_user_id] = assistant

        past_history = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user.id).order_by(models.ChatHistory.timestamp.desc()).limit(10).all()
        history_str = "\n".join([f"{msg.sender}: {msg.message_text}" for msg in reversed(past_history)])

        user_data_str = (
            f"- نام: {user.first_name}\n"
            f"- جنسیت: {user.gender}\n"
            f"- قد: {user.height_cm} سانتی‌متر\n"
            f"- وزن فعلی: {user.current_weight_kg} کیلوگرم\n"
            f"- وزن هدف: {user.target_weight_kg} کیلوگرم"
        )

        final_prompt = SYSTEM_PROMPT.format(
            user_data=user_data_str,
            history=history_str,
            task=task_prompt
        )

        raw_ai_response = assistant.get_simple_response(final_prompt)

        # --- پردازش تگ‌ها ---
        if raw_ai_response.strip().startswith("[PROCEED]"):
            should_increment_step = True
            ai_response = raw_ai_response.replace("[PROCEED]", "").strip()
        elif raw_ai_response.strip().startswith("[REPEAT]"):
            should_increment_step = False
            ai_response = raw_ai_response.replace("[REPEAT]", "").strip()
        else:
            # اگر مدل تگ را فراموش کرد، به عنوان حالت پیش‌فرض به مرحله بعد می‌رویم
            should_increment_step = True
            ai_response = raw_ai_response

    # --- آپدیت مرحله گفتگو ---
    if should_increment_step:
        user.dialogue_step += 1
        db.commit()

    # ذخیره پاسخ AI در تاریخچه
    ai_chat = models.ChatHistory(user_id=user.id, sender="ai", message_text=ai_response)
    db.add(ai_chat)
    db.commit()

    return ChatResponse(ai_response=ai_response)




# --- Endpoint جدید برای تاریخچه ---
@app.get("/chat/{telegram_user_id}/history", response_model=List[ChatHistoryResponse])
def get_chat_history(telegram_user_id: int, db: Session = Depends(get_db)):
    """
    تاریخچه چت یک کاربر خاص را برمی‌گرداند.
    """
    user = db.query(models.User).filter(models.User.telegram_user_id == telegram_user_id).first()
    if not user:
        # اگر کاربر وجود نداشت، تاریخچه خالی برمی‌گردانیم
        return []
    
    # مرتب‌سازی بر اساس زمان برای نمایش صحیح
    history = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user.id).order_by(models.ChatHistory.timestamp).all()
    return history


@app.get("/")
def read_root():
    return {"message": "Welcome to the Fit Coach AI API!"}

@app.post("/test/clear-data", status_code=status.HTTP_200_OK)
def clear_test_data(db: Session = Depends(get_db)):
    """
    !!! هشدار: این Endpoint تمام کاربران و تاریخچه چت را پاک می‌کند.
    فقط برای اهداف تست استفاده شود.
    """
    try:
        # ما از دستور SQL خام TRUNCATE استفاده می‌کنیم که بسیار سریع است
        # CASCADE به صورت خودکار رکوردهای مرتبط در chat_history را پاک می‌کند
        db.execute(text("TRUNCATE TABLE users, chat_history RESTART IDENTITY CASCADE;"))
        db.commit()
        return {"status": "success", "message": "جداول users و chat_history با موفقیت پاک شدند."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
