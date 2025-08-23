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

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.telegram_user_id not in chat_sessions:
        assistant = FitnessCoachAssistant()
        # --- بخش کلیدی جدید: تزریق حافظه (Memory Rehydration) ---
        # تاریخچه قبلی را از دیتابیس می‌خوانیم و به حافظه AI تزریق می‌کنیم
        past_history = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user.id).order_by(models.ChatHistory.timestamp).all()
        for msg in past_history:
            if msg.sender == 'user':
                assistant.memory.chat_memory.add_user_message(msg.message_text)
            else:
                assistant.memory.chat_memory.add_ai_message(msg.message_text)
        chat_sessions[user.telegram_user_id] = assistant
    
    assistant = chat_sessions[user.telegram_user_id]

    # ۳. آماده‌سازی پرامپت کامل (فقط برای اولین پیام گفتگو)
    formatted_prompt = ""
    if not assistant.memory.chat_memory.messages:
        user_data_str = (
            f"- نام: {user.first_name}\n"
            f"- جنسیت: {user.gender}\n"
            f"- قد: {user.height_cm} سانتی‌متر\n"
            f"- وزن فعلی: {user.current_weight_kg} کیلوگرم\n"
            f"- وزن هدف: {user.target_weight_kg} کیلوگرم"
        )
        exercises = db.query(models.Exercise).all()
        exercise_list_str = "\n".join([f"- {ex.name} (برای گروه عضلانی: {ex.muscle_group})" for ex in exercises])
        
        formatted_prompt = SYSTEM_PROMPT.format(
            user_data=user_data_str, 
            available_exercises=exercise_list_str
        )

    # ۴. ذخیره پیام کاربر در تاریخچه
    user_chat = models.ChatHistory(user_id=user.id, sender="user", message_text=request.message)
    db.add(user_chat)
    db.commit()

    # ۵. گرفتن پاسخ از هوش مصنوعی با متد جدید
    ai_message_text = assistant.get_response(request.message, formatted_prompt)

    # ۶. ذخیره پیام AI در تاریخچه
    ai_chat = models.ChatHistory(user_id=user.id, sender="ai", message_text=ai_message_text)
    db.add(ai_chat)
    db.commit()

    # ۷. بررسی و ذخیره برنامه نهایی
    plan_data = assistant.parse_final_response(ai_message_text)
    if plan_data and "plan" in plan_data:
        existing_plan = db.query(models.GeneratedPlan).filter(models.GeneratedPlan.user_id == user.id).first()
        if existing_plan:
            db.delete(existing_plan)
            db.commit()

        new_plan = models.GeneratedPlan(user_id=user.id, plan_type="free_generated")
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

        for day_data in plan_data["plan"]:
            for exercise_data in day_data["exercises"]:
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
