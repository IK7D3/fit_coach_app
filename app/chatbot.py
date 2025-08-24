# app/chatbot.py
import os
import json
from langchain_cohere import ChatCohere
# پرامپت تخصصی برای تولید بازخورد آنی
FEEDBACK_PROMPT = """
تو یک مربی بدنسازی هوش مصنوعی به نام «مربی‌همراه» هستی. کاربر در حال پر کردن فرم اطلاعاتش است.
او به سوال '{question}' پاسخ '{answer}' را داده است.
وظیفه تو: یک پیام کوتاه، مثبت و حمایت‌گر (حداکثر یک جمله) در واکنش به پاسخ او بنویس.
مثال: اگر به سوال 'چند روز در هفته تمرین می‌کنی؟' پاسخ داد '۳ روز'، تو بگو: 'عالیه! ۳ روز در هفته یک تعهد فوق‌العاده است.'
"""

# پرامپت تخصصی برای تولید برنامه نهایی
PLAN_GENERATION_PROMPT = """
تو یک مربی بدنسازی هوش مصنوعی متخصص به نام «مربی‌همراه» هستی.
وظیفه تو: بر اساس اطلاعات کامل کاربر که در زیر آمده، یک برنامه تمرینی هفتگی دقیق و شخصی‌سازی شده برای او در قالب یک ساختار JSON تولید کن.
برنامه باید کاملاً با اهداف، محدودیت‌ها و شرایط کاربر هماهنگ باشد.

<اطلاعات_کامل_کاربر>
{user_data}
</اطلاعات_کامل_کاربر>

خروجی تو باید فقط و فقط یک ساختار JSON معتبر با فرمت زیر باشد.

<فرمت_خروجی_JSON>
{{
  "plan_summary": "یک خلاصه ۲-۳ جمله‌ای از منطق کلی برنامه و توصیه‌های اصلی",
  "weekly_plan": [
    {{
      "day": 1,
      "day_title": "مثال: بالا تنه قدرتی",
      "exercises": [
        {{"name": "پرس سینه هالتر", "sets": 4, "reps": "8-12"}}
      ]
    }}
  ]
}}
</فرمت_خروجی_JSON>

**قوانین بسیار مهم برای فیلدهای JSON:**
-   فیلد `"sets"`: این فیلد **همیشه و تحت هیچ شرایطی** باید یک **عدد صحیح (integer)** باشد.
    -   برای تمرینات قدرتی، تعداد ست را به صورت عدد بنویس (مثال: `3`, `4`).
    -   برای تمرینات هوازی یا مداوم (مثل دویدن، پیلاتس و...)، عدد **`0`** را به عنوان مقدار `"sets"` قرار بده.
    -   **هرگز** از کلماتی مانند "مداوم" یا هر متن دیگری در فیلد `"sets"` استفاده نکن.
-   فیلد `"reps"`: این فیلد همیشه باید یک **رشته متنی (string)** باشد (مثال: `"8-12"`, `"30 دقیقه"`).
"""

class FitnessCoachAssistant:
    def __init__(self):
        self.llm = ChatCohere(model="command-r", temperature=0.7)

    def get_feedback(self, question: str, answer: str) -> str:
        """ متخصص شماره ۱: تولید بازخورد آنی و کوتاه """
        try:
            prompt = FEEDBACK_PROMPT.format(question=question, answer=answer)
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"Error in feedback generation: {e}")
            return "" # در صورت خطا، پیام خالی برمی‌گردانیم

    def generate_plan(self, user_data: str) -> str:
        """ متخصص شماره ۲: تولید برنامه تمرینی نهایی در قالب JSON """
        try:
            prompt = PLAN_GENERATION_PROMPT.format(user_data=user_data)
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"Error in plan generation: {e}")
            return '{"error": "متاسفانه در تولید برنامه خطایی رخ داد."}'