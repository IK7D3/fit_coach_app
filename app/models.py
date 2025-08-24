# models.py
import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    BigInteger,
    ForeignKey,
    Text,
    Float
)
from sqlalchemy.orm import relationship, declarative_base

# ساخت کلاس پایه برای تمام مدل‌ها
Base = declarative_base()


class User(Base):
    """
    مدل کاربران (نسخه جدید)
    شامل تمام اطلاعات فیزیکی و اهداف کاربر.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # --- ستون‌های جدید برای اطلاعات کاربر ---
    gender = Column(String(50), nullable=True)  # e.g., 'male', 'female'
    height_cm = Column(Float, nullable=True)
    current_weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    dialogue_step = Column(Integer, default=0)
    # تعریف روابط (Relationships)
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    plan = relationship("GeneratedPlan", uselist=False, back_populates="user", cascade="all, delete-orphan")

    
class ChatHistory(Base):

    """
    مدل تاریخچه چت. تمام مکالمات کاربر با AI اینجا ذخیره می‌شود.
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String(50), nullable=False)  # "user" or "ai"
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # تعریف رابطه با کاربر
    user = relationship("User", back_populates="chats")


class Exercise(Base):
    """
    مدل کتابخانه حرکات. این جدول مرجع تمام حرکات است.
    """
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    muscle_group = Column(String(100))
    video_url = Column(String(512))
    description = Column(Text)


class GeneratedPlan(Base):
    """
    مدل برنامه تولید شده برای هر کاربر.
    """
    __tablename__ = "generated_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # تعریف روابط
    user = relationship("User", back_populates="plan")
    entries = relationship("PlanEntry", back_populates="plan", cascade="all, delete-orphan")


class PlanEntry(Base):
    """
    مدل جزئیات برنامه. هر ردیف، یک حرکت در یک روز خاص از برنامه است.
    """
    __tablename__ = "plan_entries"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("generated_plans.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    sets = Column(Integer)
    reps = Column(String(50))
    display_order = Column(Integer)

    # تعریف روابط
    plan = relationship("GeneratedPlan", back_populates="entries")
    exercise = relationship("Exercise")

