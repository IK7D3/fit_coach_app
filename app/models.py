# app/models.py
import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # --- اطلاعات فرم اولیه ---
    gender = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True) # ستون جدید برای سن
    height_cm = Column(Float, nullable=True)
    current_weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    workout_location = Column(String(50), nullable=True) # ستون جدید برای محل تمرین

    # --- پاسخ به سوالات کیفی ---
    body_description = Column(String(255), nullable=True)
    physical_issues = Column(Text, nullable=True)
    mirror_feeling = Column(Text, nullable=True)
    goals_motivation = Column(Text, nullable=True)
    workout_days_per_week = Column(Integer, nullable=True)
    feared_exercises = Column(Text, nullable=True)

    # --- رابطه با برنامه نهایی ---
    plan = relationship("GeneratedPlan", uselist=False, back_populates="user", cascade="all, delete-orphan")


class GeneratedPlan(Base):
    __tablename__ = "generated_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="plan")
    entries = relationship("PlanEntry", back_populates="plan", cascade="all, delete-orphan")

class PlanEntry(Base):
    __tablename__ = "plan_entries"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("generated_plans.id"), nullable=False)
    
    exercise_name = Column(String(255), nullable=False) 
    
    day_number = Column(Integer, nullable=False)
    sets = Column(Integer)
    reps = Column(String(50))
    plan = relationship("GeneratedPlan", back_populates="entries")