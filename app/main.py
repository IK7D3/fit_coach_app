# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from . import models
from .database import SessionLocal, engine
from .chatbot import FitnessCoachAssistant

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fit Coach AI API")
assistant = FitnessCoachAssistant()

# --- Pydantic Models ---
class UserFullData(BaseModel):
    telegram_user_id: int
    gender: str
    age: int
    height_cm: float
    current_weight_kg: float
    target_weight_kg: float
    workout_location: str
    body_description: str
    physical_issues: str
    mirror_feeling: str
    goals_motivation: str
    workout_days_per_week: int
    feared_exercises: str

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    
class RegisterRequest(BaseModel):
    telegram_user_id: int
    first_name: str | None = None

class PlanGenerationRequest(BaseModel):
    telegram_user_id: int

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---
@app.post("/submit-form")
def submit_full_form(data: UserFullData, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_user_id == data.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # آپدیت تمام فیلدهای کاربر با اطلاعات فرم
    for field, value in data.dict().items():
        if field != "telegram_user_id":
            setattr(user, field, value)
    
    db.commit()
    return {"status": "success", "message": "User data fully updated."}

@app.post("/get-ai-feedback")
def get_ai_feedback(request: FeedbackRequest):
    feedback = assistant.get_feedback(question=request.question, answer=request.answer)
    return {"feedback_text": feedback}

@app.post("/generate-plan")
def generate_plan(request: PlanGenerationRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_user_id == request.telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ساخت یک رشته کامل از تمام اطلاعات کاربر برای ارسال به AI
    user_data_str = f"""
- نام: {user.first_name}
- جنسیت: {user.gender}
- سن: {user.age}
- قد: {user.height_cm} سانتی‌متر
- وزن فعلی: {user.current_weight_kg} کیلوگرم
- وزن هدف: {user.target_weight_kg} کیلوگرم
- محل تمرین: {user.workout_location}
- توصیف بدن: {user.body_description}
- مشکلات فیزیکی: {user.physical_issues}
- حس در آینه: {user.mirror_feeling}
- انگیزه اصلی: {user.goals_motivation}
- روزهای تمرین در هفته: {user.workout_days_per_week}
- حرکات نگران‌کننده: {user.feared_exercises}
    """
    
    raw_plan = assistant.generate_plan(user_data=user_data_str.strip())
    # در اینجا می‌توانید برنامه را در دیتابیس هم ذخیره کنید (جداول GeneratedPlan)
    
    return {"raw_plan_response": raw_plan}
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


@app.get("/")
def read_root():
    return {"message": "Welcome to the Fit Coach AI API!"}

