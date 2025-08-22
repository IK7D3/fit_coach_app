# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://fit_coach_db_user:bqzDQR2djMnTWOahbWvSM8BIlJ2OHirO@dpg-d2jmobqli9vc73c0f740-a/fit_coach_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)