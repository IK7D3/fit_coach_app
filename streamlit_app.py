# streamlit_app.py
import streamlit as st
import requests

# --- تنظیمات اولیه ---
API_BASE_URL = "https://fitcoachapp-production.up.railway.app" # آدرس پایه API شما
FORM_API_URL = f"{API_BASE_URL}/users/form-data"
CHAT_API_URL = f"{API_BASE_URL}/chat"
HISTORY_API_URL = f"{API_BASE_URL}/chat/{{user_id}}/history"

# --- توابع اصلی ---

def display_form_step_1():
    st.header("مرحله ۱: جنسیت")
    st.selectbox(
        "جنسیت خود را انتخاب کنید:",
        ("مرد", "زن"),
        key="gender_input",
        index=None,
        placeholder="انتخاب کنید..."
    )
    if st.button("مرحله بعد", use_container_width=True, type="primary"):
        if st.session_state.gender_input:
            st.session_state.form_step = 2
            st.rerun()
        else:
            st.warning("لطفاً جنسیت خود را انتخاب کنید.")

def display_form_step_2():
    st.header("مرحله ۲: مشخصات فیزیکی")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("قد شما (سانتی‌متر)", min_value=100, max_value=250, key="height_input")
    with col2:
        st.number_input("وزن فعلی شما (کیلوگرم)", min_value=30.0, max_value=200.0, key="current_weight_input", format="%.1f")
    
    if st.button("مرحله بعد", use_container_width=True, type="primary"):
        if st.session_state.height_input > 100 and st.session_state.current_weight_input > 30:
            st.session_state.form_step = 3
            st.rerun()
        else:
            st.warning("لطفاً قد و وزن خود را به درستی وارد کنید.")

def display_form_step_3():
    st.header("مرحله ۳: هدف شما")
    st.number_input("وزن هدف شما (کیلوگرم)", min_value=30.0, max_value=200.0, key="target_weight_input", format="%.1f")

    if st.button("شروع گفتگوی هوشمند", use_container_width=True, type="primary"):
        if st.session_state.target_weight_input > 30:
            # ارسال اطلاعات به بک‌اند
            with st.spinner("در حال ذخیره اطلاعات..."):
                payload = {
                    "telegram_user_id": st.session_state.telegram_user_id,
                    "gender": st.session_state.gender_input.lower(),
                    "height_cm": st.session_state.height_input,
                    "current_weight_kg": st.session_state.current_weight_input,
                    "target_weight_kg": st.session_state.target_weight_input
                }
                try:
                    response = requests.post(FORM_API_URL, json=payload)
                    response.raise_for_status()
                    st.session_state.form_step = 4 # برو به مرحله چت
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"خطا در ذخیره اطلاعات: {e}")
        else:
            st.warning("لطفاً وزن هدف خود را به درستی وارد کنید.")

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
                # --- اینجا اصلاح شد ---
                response = requests.post(CHAT_API_URL, json=payload)
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
    st.title("به دستیار هوشمند مربی خوش آمدید! �")

    # مقداردهی اولیه session_state
    if 'initialized' not in st.session_state:
        query_params = st.query_params
        user_id = query_params.get("user_id")
        first_name = query_params.get("first_name")

        st.session_state.telegram_user_id = int(user_id) if user_id else 99999
        st.session_state.first_name = first_name or "کاربر تستی"
        
        st.session_state.messages = []
        st.session_state.plan_received = False
        st.session_state.form_step = 1 # شروع از مرحله اول فرم
        st.session_state.initialized = True
    
    # نمایش صفحه مناسب بر اساس مرحله فعلی
    if st.session_state.form_step == 1:
        display_form_step_1()
    elif st.session_state.form_step == 2:
        display_form_step_2()
    elif st.session_state.form_step == 3:
        display_form_step_3()
    elif st.session_state.form_step == 4:
        # اگر تاریخچه خالی بود، اولین پیام را از بک‌اند بگیر
        if not st.session_state.messages:
            send_message_to_backend("start")
        
        if st.session_state.plan_received:
            display_workout_plan(st.session_state.plan_data)
        else:
            display_chat_interface()


if __name__ == "__main__":
    main()