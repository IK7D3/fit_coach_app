# app/chatbot.py
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# پرامپت تخصصی برای ماژول تشخیص قصد
INTENT_RECOGNITION_PROMPT = """
تو یک مدل زبان هستی که فقط برای طبقه‌بندی پیام کاربر استفاده می‌شوی.
سوال پرسیده شده از کاربر این بود: '{question}'
پیام کاربر این است: '{user_message}'

بر اساس پیام کاربر، قصد او کدام یک از موارد زیر است؟
- ANSWER: کاربر در حال پاسخ دادن به سوال است. (مثال: 'بله دیسک کمر دارم'، '3 روز در هفته'، 'میخوام بازوهام بزرگ بشه')
- QUESTION: کاربر در حال پرسیدن یک سوال متقابل است. (مثال: 'چطوری درصد چربی بگیرم؟'، 'منظورت چیه؟')
- REFUSAL: کاربر از پاسخ دادن امتناع می‌کند. (مثال: 'نمیخوام بگم'، 'به تو چه')
- IRRELEVANT: حرف او کاملاً بی‌ربط است. (مثال: 'هوا چطوره؟')

فقط و فقط یکی از کلمات کلیدی بالا (ANSWER, QUESTION, REFUSAL, IRRELEVANT) را به عنوان خروجی برگردان.
"""

# پرامپت تخصصی برای ماژول تولید پاسخ
RESPONSE_GENERATION_PROMPT = """
تو یک مربی بدنسازی هوش مصنوعی به نام «مربی‌همراه» هستی. لحن تو حمایت‌گر، حرفه‌ای و الهام‌بخش است.
اطلاعات کاربر: {user_data}
تاریخچه اخیر گفتگو: {history}
وظیفه فعلی تو این است: {task}
"""

class FitnessCoachAssistant:
    def __init__(self):
        # ما از دو مدل مختلف می‌توانیم استفاده کنیم، یکی برای سرعت، یکی برای کیفیت
        # اما برای سادگی، فعلا از یک مدل برای هر دو کار استفاده می‌کنیم.
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

    def recognize_intent(self, question: str, user_message: str) -> str:
        """
        متخصص شماره ۱: تشخیص قصد کاربر
        """
        try:
            prompt = INTENT_RECOGNITION_PROMPT.format(question=question, user_message=user_message)
            response = self.llm.invoke(prompt)
            intent = response.content.strip().upper()
            
            # اطمینان از اینکه خروجی یکی از گزینه‌های معتبر است
            if intent in ["ANSWER", "QUESTION", "REFUSAL", "IRRELEVANT"]:
                return intent
            return "IRRELEVANT" # اگر مدل پاسخ نامعتبری داد
        except Exception as e:
            print(f"Error in intent recognition: {e}")
            return "IRRELEVANT"

    def generate_response(self, user_data: str, history: str, task: str) -> str:
        """
        متخصص شماره ۲: تولید پاسخ نهایی برای کاربر
        """
        try:
            prompt = RESPONSE_GENERATION_PROMPT.format(user_data=user_data, history=history, task=task)
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"Error in response generation: {e}")
            return "متاسفانه در حال حاضر مشکلی در ارتباط با سرور پیش آمده. لطفاً کمی بعد دوباره تلاش کنید."
    
    @staticmethod
    def parse_final_response(ai_response: str):
        # این متد بدون تغییر باقی می‌ماند
        try:
            if "```json" in ai_response:
                clean_response = ai_response.split("```json")[1].split("```")[0].strip()
            else:
                start_index = ai_response.find('{')
                end_index = ai_response.rfind('}')
                if start_index != -1 and end_index != -1:
                    clean_response = ai_response[start_index : end_index + 1]
                else: return None
            return json.loads(clean_response)
        except (json.JSONDecodeError, IndexError):
            return None