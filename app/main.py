# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from . import models
from .database import SessionLocal, engine
from .chatbot import FitnessCoachAssistant
import json

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
    
    # --- تلاش اول برای تولید برنامه ---
    raw_plan_response = assistant.generate_plan(user_data=user_data_str.strip())
    plan_data = None
    
    # --- حلقه اصلاح خودکار (منطق نگهبان) ---
    try:
        # ۱. تلاش برای پیدا کردن و پارس کردن JSON
        json_start = raw_plan_response.find('{')
        json_end = raw_plan_response.rfind('}')
        if json_start != -1 and json_end != -1:
            plan_str = raw_plan_response[json_start:json_end+1]
            plan_data = json.loads(plan_str)
        else:
            raise ValueError("ساختار اولیه JSON یافت نشد.")

    except json.JSONDecodeError as e:
        print(f"Initial JSON parsing failed: {e}. Attempting self-correction...")
        try:
            # ۲. اگر تلاش اول ناموفق بود، از متخصص اصلاح JSON کمک می‌گیریم
            corrected_response = assistant.fix_json(broken_json=plan_str, error=str(e))
            
            # ۳. دوباره برای پیدا کردن و پارس کردن JSON اصلاح شده تلاش می‌کنیم
            json_start = corrected_response.find('{')
            json_end = corrected_response.rfind('}')
            if json_start != -1 and json_end != -1:
                corrected_plan_str = corrected_response[json_start:json_end+1]
                plan_data = json.loads(corrected_plan_str)
                print("Self-correction successful!")
            else:
                raise ValueError("ساختار JSON اصلاح شده نیز یافت نشد.")

        except (ValueError, json.JSONDecodeError) as final_e:
            print(f"Self-correction failed: {final_e}")
            # اگر اصلاح هم ناموفق بود، تسلیم می‌شویم
            plan_data = None
    # --------------------------------------------------

    # --- ذخیره در دیتابیس (فقط اگر plan_data معتبر باشد) ---
    if plan_data:
        try:
            existing_plan = db.query(models.GeneratedPlan).filter(models.GeneratedPlan.user_id == user.id).first()
            if existing_plan:
                db.delete(existing_plan)
                db.commit()

            new_plan = models.GeneratedPlan(user_id=user.id)
            db.add(new_plan)
            db.flush()

            for day_plan in plan_data.get('weekly_plan', []):
                day_num = day_plan.get('day')
                for exercise in day_plan.get('exercises', []):
                    # ... (منطق تمیز کردن sets بدون تغییر است)
                    sets_value = exercise.get('sets')
                    cleaned_sets = 0
                    try:
                        cleaned_sets = int(sets_value)
                    except (ValueError, TypeError):
                        cleaned_sets = 0
                    
                    plan_entry = models.PlanEntry(plan_id=new_plan.id, day_number=day_num, exercise_name=exercise.get('name'), sets=cleaned_sets, reps=str(exercise.get('reps', '')))
                    db.add(plan_entry)
            
            db.commit()
            print(f"Plan successfully saved for user {user.telegram_user_id}")

        except Exception as db_e:
            print(f"Error saving VALID plan to DB: {db_e}")
            db.rollback()

    return {"raw_plan_response": raw_plan_response}

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



@app.get("/debug/clear-all-data")
def clear_all_data_for_testing(db: Session = Depends(get_db)):
    """
    !!! هشدار: این اندپوینت تمام داده‌ها را از تمام جداول پاک می‌کند !!!
    فقط برای تست و توسعه استفاده شود و قبل از انتشار نهایی حذف گردد.
    """
    try:
        # پاک کردن باید به ترتیب معکوس وابستگی‌ها انجام شود تا خطای ForeignKey رخ ندهد.
        # اول جزئیات (plan_entries)
        num_plan_entries_deleted = db.query(models.PlanEntry).delete()
        # بعد خود برنامه‌ها (generated_plans)
        num_generated_plans_deleted = db.query(models.GeneratedPlan).delete()
        # و در آخر کاربران (users)
        num_users_deleted = db.query(models.User).delete()

        db.commit()
        
        message = (
            f"Success! All data has been cleared.\n"
            f"- Deleted {num_users_deleted} users.\n"
            f"- Deleted {num_generated_plans_deleted} generated plans.\n"
            f"- Deleted {num_plan_entries_deleted} plan entries."
        )
        print(message)
        return {"status": "success", "details": message}

    except Exception as e:
        db.rollback()
        print(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")
