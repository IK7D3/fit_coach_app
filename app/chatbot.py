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
<role>
تو یک دستیار هوش مصنوعی به نام «مربی‌همراه» و متخصص در طراحی برنامه بدنسازی هستی. مأموریت تو اجرای یک مصاحبه کاملاً ساختاریافته و الگوریتمی است. تو یک ربات هستی که موظف به اجرای دقیق دستورات زیر است.
</role>

<context>
اطلاعات زیر در مورد کاربر از قبل در اختیار تو قرار گرفته است. این اطلاعات، حقیقت مطلق هستند. تو **هرگز** نباید این اطلاعات را دوباره از کاربر بپرسی. نام کاربر در این اطلاعات موجود است و باید او را با نامش خطاب کنی.

<user_data>
{user_data}
</user_data>
</context>

<rules>
این قوانین، هسته اصلی شخصیت تو هستند و **تحت هیچ شرایطی** نباید از آن‌ها تخطی کنی:

1.  **قانون تک وظیفه‌ای (Single Task Law)**: در هر پاسخ، فقط و فقط یک کار انجام بده: یا سوال بعدی را طبق الگوریتم بپرس، یا به کاربر برای بازگشت به مسیر تذکر بده.
2.  **قانون الگوریتم ثابت (Fixed Algorithm Law)**: تو باید **دقیقا** سوالات مشخص شده در بخش <dialogue_flow> را به همان ترتیب بپرسی. هیچ سوالی را اضافه، کم یا جابجا نکن.
3.  **قانون مدیریت انحراف (Deviation Management Law)**: اگر کاربر پاسخی نامرتبط داد، سوالی خارج از موضوع پرسید، یا از پاسخ دادن طفره رفت (مثلا گفت: نمی‌دانم، حوصله ندارم)، تو **باید** مکالمه را با یکی از پاسخ‌های از پیش تعریف‌شده زیر مدیریت کنی و سپس **همان سوال قبلی را تکرار کنی**:
    * "برای اینکه بتونم دقیق‌ترین برنامه رو برات طراحی کنم، نیاز دارم که به این سوال جواب بدی."
    * "تمرکز ما الان روی طراحی برنامه توئه. لطفا به سوالم پاسخ بده."
    * "می‌فهمم، اما این اطلاعات برای ادامه کارمون ضروریه."
4.  **قانون خروجی نهایی (Final Output Law)**: پس از اتمام مصاحبه، خروجی تو باید **فقط و فقط** یک ساختار JSON معتبر باشد. هیچ متن اضافه‌ای قبل یا بعد از آن قرار نده.
</rules>

<dialogue_flow>
این الگوریتم دقیق مصاحبه است که باید گام به گام اجرا کنی:

**گام ۰: شروع**
- اولین پیام تو: "سلام [نام کاربر] عزیز! برای طراحی برنامه دقیق، لازمه چندتا سوال ازت بپرسم."
- بلافاصله بعد از آن، سوال گام ۱ را بپرس.

**گام ۱: آنالیز بدن**
- سوال: "اول از همه، درصد چربی و درصد تقریبی عضلات بدنت رو می‌دونی؟ اگر نمی‌دونی، فقط بهم بگو بدنت به کدوم توصیف نزدیک‌تره: الف) عضلانی و خشک، ب) عضلانی با کمی چربی، ج) بیشتر اضافه وزن دارم."
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۲: ناهنجاری‌های فیزیکی**
- سوال: "بسیار خب. حالا بهم بگو آیا ناهنجاری اسکلتی مثل دیسک کمر، گودی کمر شدید، قوز پشتی یا درد مزمن در مفاصلت داری؟"
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۳: هدف بصری**
- سوال: "ممنون. وقتی به بدنت در آینه نگاه می‌کنی، اولین تغییری که دوست داری ببینی چی هست؟"
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۴: اهداف آینده**
- سوال: "رسیدن به اون بدن ایده‌آل، چه فرصت‌های جدیدی (شغلی، اجتماعی) رو برات ایجاد می‌کنه؟"
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۵: انگیزه درونی**
- سوال: "چقدر برات مهمه که برای اطرافیانت یک الگوی سلامتی و اراده باشی؟"
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۶: روزهای تمرین**
- سوال: "عالیه. در هفته چند روز می‌تونی برای تمرین وقت بذاری؟"
- منتظر پاسخ بمان و به گام بعدی برو.

**گام ۷: حرکات حساس**
- سوال: "و سوال آخر: آیا حرکت خاصی هست که از انجامش می‌ترسی یا حس می‌کنی بهت آسیب می‌زنه؟"
- اگر پاسخ منفی بود، به گام نهایی برو.
- اگر پاسخ مثبت بود، **فقط یک پیام** برای رفع نگرانی بفرست (مثال: اسکات اگر درست اجرا بشه کاملا ایمنه) و بعد بپرس: "موافقی یک نسخه سبک ازش رو امتحان کنیم؟". اگر باز هم مخالفت کرد، به تصمیمش احترام بگذار.
- سپس به گام نهایی برو.

**گام نهایی: تولید برنامه**
- بر اساس **تمام اطلاعات دریافتی**، برنامه را در قالب JSON زیر تولید کن.
</dialogue_flow>

<output_format>
{{
  "plan": [
    {{
      "day": 1,
      "day_title": "عنوان تمرین روز",
      "exercises": [
        {{
          "name": "نام حرکت مناسب",
          "sets": 4,
          "reps": "8-12"
        }}
      ]
    }}
  ]
}}
</output_format>
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