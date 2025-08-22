# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# خواندن آدرس دیتابیس از متغیر محیطی که در Render تنظیم کردیم
DATABASE_URL = os.getenv("DATABASE_URL")

# اگر متغیر محیطی وجود نداشت (مثلاً در حال تست روی کامپیوتر شخصی بودیم)
# از دیتابیس محلی SQLite استفاده کن
if DATABASE_URL is None:
    print("WARNING: DATABASE_URL environment variable not set. Using local SQLite database.")
    DATABASE_URL = "sqlite:///./fitness_app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)