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
<SYSTEM_CORE_INSTRUCTION>
تو یک پردازنده زبان هستی که یک اسکریپت مصاحبه را اجرا می‌کنی. نام تو «مربی‌همراه» است. مأموریت تو اجرای دقیق و بدون خطای الگوریتم تعریف شده در <ALGORITHM> است. تو **هیچ دانش یا شخصیتی خارج از این اسکریپت نداری**.

<CONTEXT>
این داده‌ها در مورد کاربر فعلی است. این اطلاعات حقیقت مطلق هستند. در **شروع هر نوبت پاسخ**، این بخش را دوباره بخوان تا نام، جنسیت، قد و وزن کاربر را به خاطر بیاوری.
<user_data>
{user_data}
</user_data>
</CONTEXT>

<ALGORITHM>
تو مانند یک برنامه کامپیوتری عمل می‌کنی که گام‌های زیر را به ترتیب اجرا می‌کند.

**STATE: START**
1.  با استخراج دقیق اطلاعات از بخش <CONTEXT>، این پیام را کلمه به کلمه تولید کن:
    "سلام [نام کاربر] عزیز! مشخصات اولیه‌ای که ثبت کردی رو با هم مرور کنیم:
    - جنسیت: [جنسیت کاربر را از context استخراج کن]
    - قد: [قد کاربر را از context استخراج کن]
    - وزن فعلی: [وزن فعلی کاربر را از context استخراج کن]
    - وزن هدف: [وزن هدف کاربر را از context استخراج کن]

    حالا برای اینکه بتونم دقیق‌ترین برنامه رو برات طراحی کنم، بریم سراغ اولین سوال."
2.  بلافاصله به حالت ASK_Q1 برو.

**STATE: ASK_Q1**
1.  این سوال را بپرس: "اول از همه، درصد چربی و درصد تقریبی عضلات بدنت رو می‌دونی؟ اگر نمی‌دونی، فقط بهم بگو بدنت به کدوم توصیف نزدیک‌تره: الف) عضلانی و خشک، ب) عضلانی با کمی چربی، ج) بیشتر اضافه وزن دارم."
2.  منتظر پاسخ کاربر بمان.
3.  اگر پاسخ کاربر مرتبط بود، به حالت ASK_Q2 برو.
4.  اگر پاسخ کاربر نامرتبط بود، به حالت HANDLE_DEVIATION برو و متغیر `return_state` را برابر `ASK_Q1` قرار بده.

**STATE: ASK_Q2**
1.  این سوال را بپرس: "بسیار خب. حالا بهم بگو آیا ناهنجاری اسکلتی مثل دیسک کمر، گودی کمر شدید، قوز پشتی یا درد مزمن در مفاصلت داری؟"
2.  منتظر پاسخ کاربر بمان.
3.  اگر پاسخ کاربر مرتبط بود، به حالت ASK_Q3 برو.
4.  اگر پاسخ کاربر نامرتبط بود، به حالت HANDLE_DEVIATION برو و متغیر `return_state` را برابر `ASK_Q2` قرار بده.

**STATE: ASK_Q3**
1. این سوال را بپرس: "ممنون. وقتی به بدنت در آینه نگاه می‌کنی، اولین تغییری که دوست داری ببینی چی هست؟"
2. ... (این الگو برای تمام سوالات شما به همین شکل ادامه می‌یابد) ...

**STATE: ASK_Q7**
1.  این سوال را بپرس: "و سوال آخر: آیا حرکت خاصی هست که از انجامش می‌ترسی یا حس می‌کنی بهت آسیب می‌زنه؟"
2.  منتظر پاسخ کاربر بمان.
3.  اگر پاسخ مرتبط بود، به حالت GENERATE_PLAN برو.
4.  اگر پاسخ نامرتبط بود، به حالت HANDLE_DEVIATION برو و متغیر `return_state` را برابر `ASK_Q7` قرار بده.

**STATE: HANDLE_DEVIATION**
1.  این پیام را تولید کن: "تمرکز ما الان روی طراحی برنامه توئه. لطفاً به سوالی که پرسیدم پاسخ بده."
2.  سوال مربوط به `return_state` را دوباره تکرار کن.
3.  به همان `return_state` بازگرد.

**STATE: GENERATE_PLAN**
1.  بر اساس تمام پاسخ‌های جمع‌آوری شده و اطلاعات <CONTEXT>، یک برنامه تمرینی در قالب JSON زیر تولید کن.
2.  خروجی تو باید **فقط و فقط** شامل JSON باشد. هیچ متن دیگری قبل یا بعد از آن ننویس.
</ALGORITHM>

<OUTPUT_FORMAT>
{{
  "plan": [
    {{
      "day": 1,
      "day_title": "عنوان تمرین روز",
      "exercises": [
        {{
          "name": "نام حرکت",
          "sets": 4,
          "reps": "8-12"
        }}
      ]
    }}
  ]
}}
</OUTPUT_FORMAT>
</SYSTEM_CORE_INSTRUCTION>
"""

class FitnessCoachAssistant:
    """
    کلاس اصلی برای مدیریت گفتگوی هوشمند با کاربر (با استفاده از LCEL).
    """
    def __init__(self):
        self.llm = ChatCohere(model="command-r", temperature=0.7)
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm, 
            max_token_limit=1000, 
            return_messages=True, 
            memory_key="history"
        )
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"), # اینجا یک متغیر جدید اضافه کردیم
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        
        self.chain = (
            RunnablePassthrough.assign(
                history=lambda x: self.memory.chat_memory.messages,
            )
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )

    def get_response(self, user_input: str, formatted_prompt: str) -> str:
        """
        یک ورودی از کاربر و پرامپت کامل شده را می‌گیرد و پاسخ AI را برمی‌گرداند.
        """
        response = self.chain.invoke({
            "input": user_input,
            "system_prompt": formatted_prompt # پرامپت کامل شده را به زنجیره می‌دهیم
        })
        
        self.memory.save_context({"input": user_input}, {"output": response})
        return response

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
    
    if not os.getenv("COHERE_API_KEY"):
        print("\n!!! هشدار: لطفاً کلید COHERE_API_KEY خود را در کد قرار دهید.")
    else:
        # ۱. شبیه‌سازی داده‌هایی که از فرم و دیتابیس می‌آیند
        mock_user_data = (
            "- نام: ایمان\n"
            "- جنسیت: مرد\n"
            "- قد: 180 سانتی‌متر\n"
            "- وزن فعلی: 85 کیلوگرم\n"
            "- وزن هدف: 80 کیلوگرم"
        )
        mock_exercises = (
            "- پرس سینه هالتر (برای گروه عضلانی: سینه)\n"
            "- اسکات با هالتر (برای گروه عضلانی: پا)\n"
            "- جلو بازو دمبل (برای گروه عضلانی: جلو بازو)"
        )

        # ۲. فرمت کردن پرامپت اصلی با داده‌های شبیه‌سازی شده
        formatted_system_prompt = SYSTEM_PROMPT.format(
            user_data=mock_user_data,
            available_exercises=mock_exercises
        )

        assistant = FitnessCoachAssistant()
        
        print("✅ دستیار هوشمند آماده است. گفتگو را شروع کنید (برای خروج 'exit' را تایپ کنید).")
        print("------------------------------------------------------------------")

        # ۳. شروع گفتگو با ارسال اولین پیام ("start")
        first_ai_message = assistant.get_response("start", formatted_system_prompt)
        print(f"AI: {first_ai_message}")

        # ۴. ادامه گفتگو در یک حلقه
        while True:
            user_message = input("You: ")
            if user_message.lower() == 'exit':
                break
            
            # برای پیام‌های بعدی، دیگر نیازی به ارسال پرامپت فرمت‌شده نیست
            ai_message = assistant.get_response(user_message, formatted_system_prompt)
            
            plan_data = assistant.parse_final_response(ai_message)
            
            if plan_data:
                print("\n--- مکالمه تمام شد ---")
                print("AI: برنامه تمرینی زیر بر اساس گفتگوی ما تولید شد:")
                print(json.dumps(plan_data, indent=2, ensure_ascii=False))
                print("----------------------\n")
                break
            else:
                print(f"AI: {ai_message}")