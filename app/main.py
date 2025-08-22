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
    کاربر را ثبت‌نام کرده و گفتگوی اولیه را در دیتابیس ایجاد می‌کند.
    """
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    
    # اگر کاربر وجود نداشت، آن را می‌سازیم و اولین گفتگو را ایجاد می‌کنیم
    if not user:
        # ساخت کاربر
        user = models.User(telegram_user_id=request.telegram_user_id, first_name=request.first_name)
        db.add(user)
        db.commit()
        db.refresh(user)

        # ایجاد اولین گفتگو در پشت صحنه
        assistant = FitnessCoachAssistant()
        
        # ۱. ذخیره پیام اولیه کاربر
        user_chat = models.ChatHistory(user_id=user.id, sender="user", message_text="start")
        db.add(user_chat)
        
        # ۲. گرفتن و ذخیره پاسخ AI
        ai_response = assistant.get_response("start")
        ai_chat = models.ChatHistory(user_id=user.id, sender="ai", message_text=ai_response)
        db.add(ai_chat)
        db.commit()

    return {"status": "success", "message": "User registered and conversation initiated."}

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

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    این Endpoint اصلی برای مدیریت گفتگوی کاربر است.
    """
    # ۱. پیدا کردن کاربر (دیگر کاربر جدید نمی‌سازیم، چون باید از قبل ثبت‌نام کرده باشد)
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    # ۲. پیدا کردن یا ساختن یک جلسه چت (Chat Session) برای کاربر
    if user.telegram_user_id not in chat_sessions:
        chat_sessions[user.telegram_user_id] = FitnessCoachAssistant()
    
    assistant = chat_sessions[user.telegram_user_id]

    # --- بخش کلیدی جدید: تزریق اطلاعات به پرامپت ---
    # اگر این اولین پیام گفتگوست، پرامپت را با اطلاعات کاربر و حرکات فرمت می‌کنیم
    if not assistant.memory.chat_memory.messages:
        # الف) استخراج اطلاعات کاربر از دیتابیس
        user_data_str = (
            f"- نام: {user.first_name}\n"
            f"- جنسیت: {user.gender}\n"
            f"- قد: {user.height_cm} سانتی‌متر\n"
            f"- وزن فعلی: {user.current_weight_kg} کیلوگرم\n"
            f"- وزن هدف: {user.target_weight_kg} کیلوگرم"
        )
        
        # ب) استخراج لیست حرکات از دیتابیس
        exercises = db.query(models.Exercise).all()
        exercise_list_str = "\n".join([f"- {ex.name} (برای گروه عضلانی: {ex.muscle_group})" for ex in exercises])
        
        # ج) فرمت کردن پرامپت نهایی با اطلاعات جدید
        formatted_prompt = SYSTEM_PROMPT.format(
            user_data=user_data_str, 
            available_exercises=exercise_list_str
        )
        
        # د) آپدیت پرامپت سیستمی در زنجیره گفتگو برای این کاربر خاص
        assistant.conversation.prompt.messages[0].prompt.template = formatted_prompt

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
    plan_data = assistant.parse_final_response(ai_message_text)
    if plan_data and "plan" in plan_data:
        # --- بخش کلیدی جدید: ذخیره برنامه در دیتابیس ---
        # ابتدا چک می‌کنیم آیا کاربر از قبل برنامه دارد یا نه و آن را حذف می‌کنیم
        existing_plan = db.query(models.GeneratedPlan).filter(models.GeneratedPlan.user_id == user.id).first()
        if existing_plan:
            db.delete(existing_plan)
            db.commit()

        # ساخت برنامه جدید
        new_plan = models.GeneratedPlan(user_id=user.id, plan_type="free_generated")
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

        # ذخیره جزئیات برنامه (حرکات)
        for day_data in plan_data["plan"]:
            for exercise_data in day_data["exercises"]:
                # پیدا کردن آبجکت حرکت در دیتابیس برای گرفتن ID آن
                exercise_obj = db.query(models.Exercise).filter(models.Exercise.name == exercise_data["name"]).first()
                if exercise_obj:
                    plan_entry = models.PlanEntry(
                        plan_id=new_plan.id,
                        exercise_id=exercise_obj.id,
                        day_number=day_data["day"],
                        sets=exercise_data["sets"],
                        reps=exercise_data["reps"],
                        display_order=day_data["exercises"].index(exercise_data)
                    )
                    db.add(plan_entry)
        db.commit()
        
        # پاک کردن جلسه چت بعد از اتمام کار
        del chat_sessions[user.telegram_user_id]
        
        return ChatResponse(
            ai_response="برنامه شما با موفقیت ساخته شد!",
            is_final=True,
            plan_data=plan_data
        )

    return ChatResponse(ai_response=ai_message_text)



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
