# app/chatbot.py
import os
import json
from langchain_cohere import ChatCohere
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# ---- تنظیمات اولیه ----
# کلید API خود را اینجا قرار دهید. بهتر است از متغیرهای محیطی استفاده کنید.
os.environ["COHERE_API_KEY"] = "kA8LXTMFKv4hawhHE6FrDdbzOx1UbdTGu7dYuf7c"

# پرامپت سیستمی که قبلاً طراحی کردیم
SYSTEM_PROMPT = """
شخصیت و نقش (Persona & Role):
تو یک دستیار هوش مصنوعی برای یک مربی بدنسازی حرفه‌ای هستی. نام تو «مربی‌همراه» است. تو بسیار خوش‌برخورد، انرژی‌بخش، متخصص و شنونده خوبی هستی. لحن تو باید دوستانه و در عین حال حرفه‌ای باشد.

زمینه (Context):
یک کاربر جدید ربات را استارت کرده است و به دنبال دریافت یک برنامه تمرینی رایگان و اولیه است. او هیچ اطلاعاتی در مورد برنامه‌ها ندارد و تو باید او را راهنمایی کنی.

هدف نهایی (Objective):
هدف تو این است که در یک گفتگوی کوتاه و طبیعی، سه اطلاعات کلیدی را از کاربر دریافت کنی:
1. هدف اصلی (Goal): کاهش وزن یا عضله‌سازی.
2. سطح تجربه (Level): مبتدی یا متوسط.
3. تعداد روزهای تمرین (Days): تعداد روزهایی که کاربر می‌تواند در هفته تمرین کند.

قوانین و محدودیت‌ها (Rules & Constraints):
1. همیشه فقط یک سوال در هر پیام بپرس.
2. پاسخ‌هایت باید کوتاه، واضح و کاملاً متمرکز بر روی گرفتن اطلاعات باشد.
3. بعد از هر پاسخ کاربر، حتماً درک خودت از پاسخ او را در یک جمله کوتاه تایید کن.
4. اگر پاسخ کاربر مبهم بود، با پرسیدن یک سوال واضح‌تر از او شفاف‌سازی بخواه.
5. به هیچ وجه توصیه پزشکی، درمانی یا مربوط به مکمل‌ها ارائه نده.
6. با یک پیام خوشامدگویی شروع کن و بلافاصله سوال اول را بپرس تا کاربر معطل نشود.

قالب خروجی (Output Format):
بسیار مهم: در انتهای مکالمه، بعد از پیام خلاصه به کاربر، باید تمام اطلاعات جمع‌آوری شده را در یک قالب JSON دقیقاً به شکل زیر برگردانی. هیچ متن اضافه‌ای قبل یا بعد از این JSON ننویس.
{{
  "goal": "weight_loss" or "muscle_gain",
  "level": "beginner" or "intermediate",
  "days_per_week": <number>
}}
"""

class FitnessCoachAssistant:
    """
    کلاس اصلی برای مدیریت گفتگوی هوشمند با کاربر.
    """
    def __init__(self):
        # ساخت مدل Cohere
        self.llm = ChatCohere(model="command-r", temperature=0.7)
        
        # ساخت Prompt Template با حافظه
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
        
        # ساخت حافظه برای ذخیره تاریخچه گفتگو
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # ساخت زنجیره گفتگو (Conversation Chain)
        self.conversation = ConversationChain(
            memory=self.memory, 
            prompt=self.prompt, 
            llm=self.llm
        )

    def get_response(self, user_input: str) -> str:
        """
        یک ورودی از کاربر می‌گیرد و پاسخ AI را برمی‌گرداند.
        """
        return self.conversation.predict(input=user_input)

    @staticmethod
    def parse_final_response(ai_response: str):
        """
        تلاش می‌کند تا پاسخ نهایی AI را به فرمت JSON پارس کند.
        """
        try:
            # گاهی AI ممکن است JSON را داخل بلاک کد ```json قرار دهد
            if "```json" in ai_response:
                clean_response = ai_response.split("```json")[1].split("```")[0].strip()
            else:
                clean_response = ai_response.strip()
            
            return json.loads(clean_response)
        except (json.JSONDecodeError, IndexError):
            # اگر پاسخ در فرمت JSON نبود، یعنی مکالمه هنوز ادامه دارد
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