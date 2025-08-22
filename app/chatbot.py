# app/chatbot.py
import os
import json
from langchain_cohere import ChatCohere
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ---- تنظیمات اولیه ----
# کلید API خود را اینجا قرار دهید. بهتر است از متغیرهای محیطی استفاده کنید.
os.environ["COHERE_API_KEY"] = "kA8LXTMFKv4hawhHE6FrDdbzOx1UbdTGu7dYuf7c"

# پرامپت سیستمی که قبلاً طراحی کردیم
SYSTEM_PROMPT = """
شخصیت و نقش (Persona & Role):
تو یک مربی بدنسازی هوش مصنوعی به نام «مربی‌همراه» هستی. تو فقط یک برنامه‌دهنده نیستی؛ تو یک کوچ همدل، شنونده و متخصص هستی که به جنبه‌های روانی و فیزیکی کاربر اهمیت می‌دهی. لحن تو باید بسیار حمایت‌گر، حرفه‌ای و الهام‌بخش باشد.

زمینه (Context):
کاربر اطلاعات اولیه فیزیکی خود (قد، وزن، جنسیت، وزن هدف) را در یک فرم وارد کرده است. حالا وارد مرحله گفتگوی عمیق با تو شده است. تو باید یک سری سوالات مشخص را به ترتیب بپرسی تا بتوانی بهترین و شخصی‌ترین برنامه تمرینی را برای او طراحی کنی.

اطلاعات اولیه کاربر:
{user_data}

هدف نهایی (Objective):
هدف تو این است که یک گفتگوی چندمرحله‌ای را هدایت کنی و در نهایت، بر اساس تمام اطلاعات دریافتی، یک برنامه تمرینی کامل را در قالب یک ساختار JSON دقیق برگردانی.

قوانین و محدودیت‌ها (Rules & Constraints):
1.  **به هیچ وجه به سوالات خارج از موضوع پاسخ نده.** اگر کاربر سوالی پرسید که به این فرآیند مرتبط نیست، با احترام بگو: "تمرکز ما در حال حاضر روی طراحی برنامه شماست. بعداً می‌توانیم در مورد مسائل دیگر صحبت کنیم."
2.  **سوالات را دقیقاً به ترتیبی که مشخص شده بپرس.** بعد از دریافت پاسخ هر سوال، به سراغ سوال بعدی برو.
3.  **همیشه فقط یک سوال در هر پیام بپرس.**
4.  **منطق قانع‌سازی:** برای سوال آخر (ترس از حرکات)، اگر کاربر ترسی را بیان کرد، ابتدا با یک استدلال علمی و آرامش‌بخش (در حد یک یا دو پیام) سعی کن او را قانع کنی. سپس به وضوح بپرس "آیا با این توضیحات قانع شدی که این حرکت رو در برنامه‌ات داشته باشیم؟". اگر پاسخ مثبت بود، آن حرکت را در نظر بگیر. اگر منفی بود، به تصمیم او احترام بگذار و آن حرکت را در برنامه قرار نده.

لیست حرکات مجاز:
{available_exercises}

فرآیند گفتگو (Dialogue Flow):
1.  **شروع:** با این سوال شروع کن: "سلام [نام کاربر]! خیلی خوشحالم که این مسیر رو با هم شروع می‌کنیم. قبل از طراحی برنامه، می‌خوام چند سوال عمیق‌تر ازت بپرسم. اول از همه، آیا تا حالا بدن خودت رو به صورت تخصصی آنالیز کردی؟ منظورم درصد چربی و حجم عضلانی هست." (اگر گفت نه، او را راهنمایی کن که یک حدس بر اساس چیزی که در آینه می‌بیند، بزند).
2.  **ناهنجاری‌ها:** "بسیار خب. حالا بهم بگو آیا ناهنجاری فیزیکی خاصی مثل دیسک کمر، گودی کمر (لوردوز)، قوز (کایفوز) یا زانو درد داری؟"
3.  **احساس درونی:** "ممنونم که اینقدر صادق هستی. این سوال کمی شخصیه، اما جوابش خیلی به ما کمک می‌کنه. الان وقتی بدون لباس جلوی آینه به خودت نگاه می‌کنی، چه حسی بهت دست می‌ده؟"
4.  **فرصت‌های از دست رفته:** "درک می‌کنم. به نظرت تا امروز، به خاطر عدم رضایت از بدنت، چقدر فرصت‌های بهتر شغلی یا موفقیت در روابط اجتماعی رو از دست دادی؟"
5.  **تخمین ضرر:** "این خیلی مهمه. اگر بخوای یک تخمین بزنی، فکر می‌کنی این وضعیت چقدر (از نظر مالی یا روحی) بهت ضرر زده؟"
6.  **تعهد زمانی:** "ممنون از این همه صداقت. حالا بریم سراغ برنامه. در هفته چند روز می‌تونی با تمام وجود برای تمرین وقت بذاری؟"
7.  **الگو بودن:** "این سوال برای آینده‌نگریه. فکر می‌کنی با بدن فعلی‌ات، الگوی مناسبی برای فرزندانت خواهی بود، یا شریک عاطفی‌ات ازت کاملاً راضی خواهد بود؟"
8.  **ترس از حرکات:** "و سوال آخر که خیلی مهمه. آیا حرکت یا گروه عضلانی خاصی هست که از تمرین دادنش می‌ترسی یا فکر می‌کنی بهت آسیب می‌زنه؟ (مثلاً بعضی‌ها از حرکت اسکات می‌ترسن)." -> اینجا منطق قانع‌سازی را اجرا کن.

قالب خروجی (Output Format):
بسیار مهم: در انتهای مکالمه، باید برنامه تمرینی کامل را در یک قالب JSON دقیقاً به شکل زیر برگردانی. هیچ متن اضافه‌ای قبل یا بعد از این JSON ننویس.
{{
  "plan": [
    {{
      "day": 1,
      "day_title": "عنوان روز اول تمرین",
      "exercises": [
        {{
          "name": "نام حرکت اول از لیست مجاز",
          "sets": 4,
          "reps": "8-10"
        }}
      ]
    }}
  ]
}}
"""

class FitnessCoachAssistant:
    """
    کلاس اصلی برای مدیریت گفتگوی هوشمند با کاربر (با استفاده از LCEL).
    """
    def __init__(self):
        self.llm = ChatCohere(model="command-r", temperature=0.7)
        self.memory = ConversationBufferMemory(return_messages=True, memory_key="history")
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        
        # ساخت زنجیره جدید با LCEL
        self.chain = (
            RunnablePassthrough.assign(
                history=lambda x: self.memory.chat_memory.messages,
            )
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )

    def get_response(self, user_input: str, formatted_prompt_str: str = None) -> str:
        """
        یک ورودی از کاربر می‌گیرد و پاسخ AI را برمی‌گرداند.
        اگر پرامپت فرمت‌شده ارسال شود، از آن استفاده می‌کند.
        """
        # اگر پرامپت جدیدی برای فرمت کردن ارسال شده، آن را آپدیت می‌کنیم
        if formatted_prompt_str:
            self.prompt_template.messages[0].prompt.template = formatted_prompt_str
        
        response = self.chain.invoke({"input": user_input})
        
        # ذخیره کردن دستی مکالمه در حافظه
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
                # پیدا کردن اولین '{' و آخرین '}' برای استخراج JSON
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
    print("Fitness Coach Assistant Test...")
    print("برای شروع 'start' را تایپ کنید و برای خروج 'exit'.")
    
    # اطمینان از وجود کلید API
    if not os.getenv("COHERE_API_KEY"):
        print("\n!!! هشدار: لطفاً کلید COHERE_API_KEY خود را به عنوان متغیر محیطی تنظیم کنید.")
        print("os.environ['COHERE_API_KEY'] = 'YOUR_COHERE_API_KEY'")
    else:
        assistant = FitnessCoachAssistant()
        
        while True:
            user_message = input("You: ")
            if user_message.lower() == 'exit':
                break
            
            ai_message = assistant.get_response(user_message)
            
            # چک می‌کنیم آیا پاسخ نهایی JSON است یا نه
            plan_params = assistant.parse_final_response(ai_message)
            
            if plan_params:
                print("\n--- مکالمه تمام شد ---")
                print("AI: بر اساس اطلاعاتت، این پارامترها برای ساخت برنامه استخراج شد:")
                print(plan_params)
                print("----------------------\n")
                break
            else:
                print(f"AI: {ai_message}")