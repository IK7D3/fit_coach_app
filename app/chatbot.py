# app/chatbot.py
import os
import json
from langchain_cohere import ChatCohere
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationSummaryBufferMemory

# ---- تنظیمات اولیه ----
# کلید API خود را اینجا قرار دهید. بهتر است از متغیرهای محیطی استفاده کنید.
os.environ["COHERE_API_KEY"] = "kA8LXTMFKv4hawhHE6FrDdbzOx1UbdTGu7dYuf7c"

# پرامپت سیستمی که قبلاً طراحی کردیم
SYSTEM_PROMPT = """
تو یک مربی بدنسازی هوش مصنوعی به نام «مربی‌همراه» هستی. لحن تو حمایت‌گر، حرفه‌ای و الهام‌بخش است. تو باید به کاربر کمک کنی تا با پاسخ دادن به چند سوال، بهترین برنامه تمرینی را دریافت کند.
اطلاعات کاربر: {user_data}
تاریخچه گفتگو: {history}
وظیفه فعلی: {task}
"""

class FitnessCoachAssistant:
    """
    نسخه ساده‌شده دستیار هوش مصنوعی.
    فقط یک وظیفه دارد: یک پرامپت کامل را دریافت کرده و پاسخ مدل را برگرداند.
    """
    def __init__(self):
        self.llm = ChatCohere(model="command-r", temperature=0.7)
        # ما دیگر به حافظه یا chain در این کلاس نیازی نداریم، چون منطق در main.py است

    def get_simple_response(self, final_prompt: str) -> str:
        """
        یک پرامپت کامل و فرمت‌شده را دریافت کرده و پاسخ مدل را برمی‌گرداند.
        """
        try:
            # ما مستقیماً پرامپت نهایی را به مدل می‌دهیم
            response = self.llm.invoke(final_prompt)
            # اگر از مدل‌های جدیدتر استفاده می‌کنید، ممکن است نیاز به .content داشته باشد
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            # مدیریت خطا در صورت بروز مشکل در ارتباط با API
            print(f"Error calling LLM: {e}")
            return "متاسفانه در حال حاضر مشکلی در ارتباط با سرور پیش آمده. لطفاً کمی بعد دوباره تلاش کنید."

    @staticmethod
    def parse_final_response(ai_response: str):
        """
        تلاش می‌کند تا پاسخ نهایی AI را به فرمت JSON پارس کند.
        """
        try:
            if "```json" in ai_response:
                clean_response = ai_response.split("```json")[1].split("```")[0].strip()
            else:
                start_index = ai_response.find('{')
                end_index = ai_response.rfind('}')
                if start_index != -1 and end_index != -1:
                    clean_response = ai_response[start_index : end_index + 1]
                else:
                    return None
            return json.loads(clean_response)
        except (json.JSONDecodeError, IndexError):
            return None

# --- بخش تست (برای اجرای مستقیم این فایل) ---
if __name__ == "__main__":
    print("--- Fitness Coach Assistant Local Test ---")
    
    # if not os.getenv("COHERE_API_KEY"):
    #     print("\n!!! هشدار: لطفاً کلید COHERE_API_KEY خود را در کد قرار دهید.")
    # else:
    #     # ۱. شبیه‌سازی داده‌هایی که از فرم و دیتابیس می‌آیند
    #     mock_user_data = (
    #         "- نام: ایمان\n"
    #         "- جنسیت: مرد\n"
    #         "- قد: 180 سانتی‌متر\n"
    #         "- وزن فعلی: 85 کیلوگرم\n"
    #         "- وزن هدف: 80 کیلوگرم"
    #     )
    #     mock_exercises = (
    #         "- پرس سینه هالتر (برای گروه عضلانی: سینه)\n"
    #         "- اسکات با هالتر (برای گروه عضلانی: پا)\n"
    #         "- جلو بازو دمبل (برای گروه عضلانی: جلو بازو)"
    #     )

    #     # ۲. فرمت کردن پرامپت اصلی با داده‌های شبیه‌سازی شده
    #     formatted_system_prompt = SYSTEM_PROMPT.format(
    #         user_data=mock_user_data,
    #         available_exercises=mock_exercises
    #     )

    #     assistant = FitnessCoachAssistant()
        
    #     print("✅ دستیار هوشمند آماده است. گفتگو را شروع کنید (برای خروج 'exit' را تایپ کنید).")
    #     print("------------------------------------------------------------------")

    #     # ۳. شروع گفتگو با ارسال اولین پیام ("start")
    #     first_ai_message = assistant.get_response("start", formatted_system_prompt)
    #     print(f"AI: {first_ai_message}")

    #     # ۴. ادامه گفتگو در یک حلقه
    #     while True:
    #         user_message = input("You: ")
    #         if user_message.lower() == 'exit':
    #             break
            
    #         # برای پیام‌های بعدی، دیگر نیازی به ارسال پرامپت فرمت‌شده نیست
    #         ai_message = assistant.get_response(user_message, formatted_system_prompt)
            
    #         plan_data = assistant.parse_final_response(ai_message)
            
    #         if plan_data:
    #             print("\n--- مکالمه تمام شد ---")
    #             print("AI: برنامه تمرینی زیر بر اساس گفتگوی ما تولید شد:")
    #             print(json.dumps(plan_data, indent=2, ensure_ascii=False))
    #             print("----------------------\n")
    #             break
    #         else:
    #             print(f"AI: {ai_message}")