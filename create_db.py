from app.models import Base, engine

print("Starting to create database and tables...")

# این دستور تمام نقشه‌هایی که در models.py تعریف کردیم را می‌خواند
# و بر اساس آن‌ها جداول را در دیتابیس می‌سازد.
Base.metadata.create_all(bind=engine)

print("Database and tables created successfully! A file named 'fitness_app.db' should now exist.")