# streamlit_app.py
import streamlit as st
import requests
import random
import time

# --- تنظیمات اولیه ---
# آدرس API که در مرحله قبل با FastAPI ساختیم
API_URL = "https://fitcoachapp-production.up.railway.app/chat"
HISTORY_API_URL = "https://fitcoachapp-production.up.railway.app/chat/{user_id}/history"

# --- توابع اصلی ---

def display_landing_screen():
    """نمایش صفحه ورودی برای جذب کاربر."""
    st.title("به دستیار هوشمند مربی خوش آمدید! 🤖")
    st.image("https://placehold.co/600x300/DBF1FF/3D4A59?text=Fit+Coach+AI", use_container_width=True)
    st.header("یک برنامه تمرینی هوشمند و رایگان دریافت کنید")
    st.markdown("""
    با پاسخ به چند سوال ساده، دستیار هوشمند ما یک برنامه تمرینی اولیه و مؤثر،
    متناسب با اهداف و سطح شما طراحی می‌کند.
    """)
    
    if st.button("🚀 شروع مصاحبه هوشمند", use_container_width=True):
        # وقتی کاربر کلیک کرد، وضعیت را تغییر می‌دهیم تا وارد صفحه چت شویم
        st.session_state['chat_started'] = True
        # ارسال پیام اولیه برای شروع گفتگو از طرف ربات
        send_message_to_backend("start")
        st.rerun() # اجرای مجدد اسکریپت برای نمایش صفحه چت

def display_chat_interface():
    st.title("💬 مصاحبه هوشمند")
    st.caption("لطفاً به سوالات دستیار هوشمند پاسخ دهید...")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("پاسخ خود را اینجا بنویسید..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        send_message_to_backend(prompt)
        st.rerun()

def display_workout_plan():
    """نمایش برنامه تمرینی نهایی."""
    st.balloons()
    st.title("🎉 برنامه تمرینی شما آماده شد!")
    st.header("بر اساس گفتگوی ما، این برنامه برای شما طراحی شد:")
    
    # TODO: در فاز بعدی، اینجا برنامه را به صورت زیبا و گرافیکی نمایش می‌دهیم.
    # فعلاً فقط پارامترهای استخراج شده را نمایش می‌دهیم.
    st.success("در قدم بعدی، این برنامه را به صورت گرافیکی با ویدیوهای آموزشی نمایش خواهیم داد.")
    st.json(st.session_state.plan_data)

    st.markdown("---")
    st.subheader("می‌خوای یک برنامه کاملاً تخصصی داشته باشی؟")
    st.info("با کلیک روی دکمه زیر، می‌تونی شرایط دریافت برنامه کاملاً شخصی‌سازی‌شده زیر نظر مستقیم مربی رو ببینی.")
    if st.button("دریافت برنامه تخصصی (به زودی)", use_container_width=True):
        st.toast("این قابلیت به زودی اضافه خواهد شد!")

def send_message_to_backend(message: str):
    """ارسال پیام به API و پردازش پاسخ."""
    with st.chat_message("assistant"):
        with st.spinner("مربی‌همراه در حال فکر کردن است..."):
            try:
                payload = {
                    "telegram_user_id": st.session_state.telegram_user_id,
                    "message": message,
                    "first_name": st.session_state.first_name
                }
                response = requests.post(API_URL, json=payload)
                response.raise_for_status() # بررسی خطاهای HTTP
                
                data = response.json()
                ai_response = data.get("ai_response")
                
                # اضافه کردن پاسخ AI به تاریخچه
                st.session_state.messages.append({"role": "assistant", "content": ai_response})

                # اگر مکالمه تمام شده بود، وضعیت را تغییر می‌دهیم
                if data.get("is_final"):
                    st.session_state.plan_received = True
                    st.session_state.plan_data = data.get("plan_data")

            except requests.exceptions.RequestException as e:
                error_message = f"خطا در ارتباط با سرور: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

def load_chat_history():
    """تاریخچه چت کاربر را از بک‌اند بارگذاری می‌کند."""
    user_id = st.session_state.telegram_user_id
    try:
        response = requests.get(HISTORY_API_URL.format(user_id=user_id))
        response.raise_for_status()
        history = response.json()
        
        formatted_history = []
        for msg in history:
            role = "user" if msg["sender"] == "user" else "assistant"
            formatted_history.append({"role": role, "content": msg["message_text"]})
        
        st.session_state.messages = formatted_history
    except requests.exceptions.RequestException as e:
        st.error(f"خطا در بارگذاری تاریخچه: {e}")


# --- منطق اصلی برنامه ---
def main():
    st.set_page_config(page_title="مربی هوشمند", page_icon="🤖")

    if 'initialized' not in st.session_state:
        query_params = st.query_params
        user_id = query_params.get("user_id")
        first_name = query_params.get("first_name")

        st.session_state.telegram_user_id = int(user_id) if user_id else 99999
        st.session_state.first_name = first_name or "کاربر تستی"
        
        # فقط تاریخچه را بارگذاری می‌کنیم
        load_chat_history()
        
        st.session_state.initialized = True
        st.session_state.plan_received = False # باید چک کنیم آیا برنامه قبلاً ساخته شده یا نه

    if st.session_state.plan_received:
        display_workout_plan()
    else:
        display_chat_interface()


if __name__ == "__main__":
    main()