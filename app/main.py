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
    # step 0
    "اول از همه، درصد چربی و درصد تقریبی عضلات بدنت رو می‌دونی؟ اگر نمی‌دونی، فقط بهم بگو بدنت به کدوم توصیف نزدیک‌تره: الف) عضلانی و خشک، ب) عضلانی با کمی چربی، ج) بیشتر اضافه وزن دارم.",
    # step 1
    "بسیار خب. حالا بهم بگو آیا ناهنجاری اسکلتی مثل دیسک کمر، گودی کمر شدید، قوز پشتی یا درد مزمن در مفاصلت داری؟",
    # step 2
    "ممنون. وقتی به بدنت در آینه نگاه می‌کنی، اولین تغییر مثبتی که دوست داری ببینی چی هست؟ (مثلا شکم صاف‌تر، بازوهای حجیم‌تر، یا فرم بهتر پاها)",
    # step 3
    "درک می‌کنم. رسیدن به این هدف، چه فرصت‌های جدیدی رو در زندگی شخصی یا شغلی برات باز می‌کنه؟",
    # step 4
    "عالیه. حالا بریم سراغ برنامه‌ریزی. در هفته چند روز می‌تونی با تمرکز کامل برای تمرین وقت بذاری؟",
    # step 5
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

    assistant = chat_sessions.get(user.telegram_user_id, FitnessCoachAssistant())
    chat_sessions[user.telegram_user_id] = assistant

    current_step = user.dialogue_step
    task_for_generator = ""

    # --- مرحله ۱: تحلیل ورودی ---
    if current_step == 0:
        intent = "ANSWER" # فرض می‌کنیم پیام "start" همیشه یک پاسخ معتبر است
    else:
        previous_question = DIALOGUE_QUESTIONS[current_step - 1]
        intent = assistant.recognize_intent(question=previous_question, user_message=request.message)
    
    print(f"User: {user.telegram_user_id}, Step: {current_step}, Intent: {intent}") # برای دیباگ

    # --- مرحله ۲: مدیریت گفتگو (مغز پایتون) ---
    if user.repeat_count >= 2:
        user.dialogue_step += 1
        user.repeat_count = 0
        if user.dialogue_step < len(DIALOGUE_QUESTIONS):
            next_question = DIALOGUE_QUESTIONS[user.dialogue_step]
            task_for_generator = f"به کاربر بگو 'ظاهرا از پاسخ به این سوال ممانعت داری، اوکی بگذریم بریم سوال بعد...'. سپس بلافاصله این سوال جدید را بپرس: '{next_question}'"
        else:
            task_for_generator = "به کاربر بگو تمام سوالات پرسیده شد و برنامه در حال آماده‌سازی است."
    
    elif intent == "ANSWER":
        user.dialogue_step += 1
        user.repeat_count = 0
        if user.dialogue_step < len(DIALOGUE_QUESTIONS):
            next_question = DIALOGUE_QUESTIONS[user.dialogue_step]
            task_for_generator = f"پاسخ کاربر را با یک عبارت مثبت کوتاه (مثل عالیه یا بسیار خب) تایید کن و سپس این سوال را بپرس: '{next_question}'"
        else:
            task_for_generator = "به کاربر بگو تمام سوالات پرسیده شد و برنامه در حال آماده‌سازی است."

    elif intent in ["QUESTION", "REFUSAL", "IRRELEVANT"]:
        user.repeat_count += 1
        previous_question = DIALOGUE_QUESTIONS[current_step - 1]
        if intent == "QUESTION":
            task_for_generator = f"ابتدا به سوال کاربر '{request.message}' پاسخ کوتاهی بده، سپس سوال قبلی یعنی '{previous_question}' را دوباره بپرس."
        else: # REFUSAL or IRRELEVANT
            task_for_generator = f"به کاربر با احترام بگو روی موضوع متمرکز بماند و سوال قبلی یعنی '{previous_question}' را دوباره بپرس."

    # مدیریت پیام خوشامدگویی در اولین مرحله
    if current_step == 0:
        user_info = (f"جنسیت: {user.gender}, قد: {user.height_cm} سانتی‌متر, وزن فعلی: {user.current_weight_kg} کیلوگرم, وزن هدف: {user.target_weight_kg} کیلوگرم")
        first_question = DIALOGUE_QUESTIONS[0]
        task_for_generator = (f"این اولین پیام به کاربر '{user.first_name}' است. به او خوشامد بگو و مشخصاتش را به این شکل نمایش بده: {user_info}. سپس بلافاصله این سوال را بپرس: '{first_question}'")

    # --- مرحله ۳: تولید پاسخ ---
    past_history = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user.id).order_by(models.ChatHistory.timestamp.desc()).limit(10).all()
    history_str = "\n".join([f"{msg.sender}: {msg.message_text}" for msg in reversed(past_history)])
    user_data_str = (f"نام: {user.first_name}, جنسیت: {user.gender}, قد: {user.height_cm}, وزن فعلی: {user.current_weight_kg}, وزن هدف: {user.target_weight_kg}")
    
    ai_response = assistant.generate_response(
        user_data=user_data_str,
        history=history_str,
        task=task_for_generator
    )

    db.commit() # ذخیره تغییرات در user.dialogue_step و user.repeat_count
    
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
