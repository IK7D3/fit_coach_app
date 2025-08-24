# streamlit_app.py
import streamlit as st
import requests
import time
import json

API_BASE_URL = "https://fitcoachapp-production.up.railway.app"

def initialize_session_state():
    if 'initialized' not in st.session_state:
        query_params = st.query_params
        st.session_state.telegram_user_id = int(query_params.get("user_id", 0))
        st.session_state.first_name = query_params.get("first_name", "کاربر")
        
        st.session_state.form_data = {
            "gender": "مرد", "height_cm": 175.0, "current_weight_kg": 70.0, "target_weight_kg": 65.0,
            "age": 25, "workout_location": "باشگاه", "body_description": "عضلانی با کمی چربی",
            "physical_issues": "هیچکدام", "mirror_feeling": "", "goals_motivation": "",
            "workout_days_per_week": 3, "feared_exercises": "هیچکدام"
        }
        st.session_state.feedback = {}
        st.session_state.page = "form"
        st.session_state.initialized = True

def get_ai_feedback(question, field_name):
    answer = st.session_state.form_data.get(field_name)
    if answer:
        try:
            response = requests.post(f"{API_BASE_URL}/get-ai-feedback", json={"question": question, "answer": str(answer)})
            if response.status_code == 200:
                st.session_state.feedback[field_name] = response.json().get("feedback_text")
        except requests.RequestException:
            pass

def display_feedback(field_name):
    if feedback_text := st.session_state.feedback.get(field_name):
        st.info(f"🤖 **مربی‌همراه:** {feedback_text}")

def display_smart_form():
    st.header(f"سلام {st.session_state.first_name} عزیز! لطفاً فرم زیر را کامل کن.")
    st.markdown("---")

    with st.container(border=True):
        st.subheader("۱. اطلاعات پایه")
        col1, col2 = st.columns(2)
        # --- فیلدهای جدید اضافه شده ---
        st.session_state.form_data['gender'] = col1.radio("جنسیت", ["مرد", "زن"], horizontal=True, key="gender")
        st.session_state.form_data['age'] = col2.number_input("سن", 15, 80, st.session_state.form_data['age'], key="age")
        
        col3, col4, col5 = st.columns(3)
        st.session_state.form_data['height_cm'] = col3.number_input("قد (سانتی‌متر)", 140.0, 220.0, st.session_state.form_data['height_cm'], key="height")
        st.session_state.form_data['current_weight_kg'] = col4.number_input("وزن فعلی (کیلوگرم)", 40.0, 200.0, st.session_state.form_data['current_weight_kg'], key="c_weight")
        st.session_state.form_data['target_weight_kg'] = col5.number_input("وزن هدف (کیلوگرم)", 40.0, 200.0, st.session_state.form_data['target_weight_kg'], key="t_weight")
        
        st.session_state.form_data['workout_location'] = st.radio("کجا تمرین می‌کنی؟", ["باشگاه", "خونه"], horizontal=True, key="location", on_change=get_ai_feedback, args=("محل تمرین", 'workout_location'))
        display_feedback('workout_location')

    # ... (بقیه بخش‌های فرم بدون تغییر زیاد)
    with st.container(border=True):
        st.subheader("۲. شرایط فعلی")
        body_options = ["عضلانی و خشک", "عضلانی با کمی چربی", "بیشتر اضافه وزن دارم", "سایر"]
        body_choice = st.radio("بدنت به کدوم توصیف نزدیک‌تره؟", body_options, index=1, horizontal=True)
        if body_choice == "سایر":
            st.session_state.form_data['body_description'] = st.text_input("توصیف خود را بنویسید:", key="body_desc_other")
        else:
            st.session_state.form_data['body_description'] = body_choice
        
        issues_options = ["هیچکدام", "دیسک کمر", "زانو درد", "گودی کمر", "قوز", "سایر"]
        issues_choice = st.multiselect("آیا ناهنجاری فیزیکی خاصی داری؟", issues_options, default="هیچکدام")
        if "سایر" in issues_choice:
            st.session_state.form_data['physical_issues'] = st.text_area("لطفاً مشکلات خود را توضیح دهید:", key="issues_other")
        else:
            st.session_state.form_data['physical_issues'] = ", ".join(issues_choice)

    with st.container(border=True):
        st.subheader("۳. اهداف و انگیزه‌ها")
        st.session_state.form_data['mirror_feeling'] = st.text_area("اولین تغییر مثبتی که دوست داری در آینه ببینی چیست؟", key="mirror")
        st.session_state.form_data['goals_motivation'] = st.text_area("رسیدن به این هدف، چه فرصت‌های جدیدی برایت باز می‌کند؟", key="motivation")

    with st.container(border=True):
        st.subheader("۴. برنامه و محدودیت‌ها")
        st.session_state.form_data['workout_days_per_week'] = st.slider("چند روز در هفته می‌تونی تمرین کنی؟", 1, 7, 3, key="days_slider")
        feared_options = ["هیچکدام", "حرکات پا (اسکات)", "حرکات سنگین کمر (ددلیفت)", "سایر"]
        feared_choice = st.multiselect("آیا حرکت خاصی هست که از انجام دادنش بترسی؟", feared_options, default="هیچکدام")
        if "سایر" in feared_choice:
            st.session_state.form_data['feared_exercises'] = st.text_area("لطفاً حرکات مورد نظر را بنویسید:", key="feared_other")
        else:
            st.session_state.form_data['feared_exercises'] = ", ".join(feared_choice)

    st.markdown("---")
    
    if st.button("🚀 برنامه من را بساز!", use_container_width=True, type="primary"):
        submit_full_form()

def submit_full_form():
    with st.spinner("در حال ارسال اطلاعات و ساختن برنامه... این ممکن است کمی طول بکشد..."):
        try:
            full_payload = {
                "telegram_user_id": st.session_state.telegram_user_id,
                **st.session_state.form_data
            }
            
            # --- خط مهمی که از کامنت خارج شد ---
            response = requests.post(f"{API_BASE_URL}/submit-form", json=full_payload)
            response.raise_for_status()

            plan_req_payload = {"telegram_user_id": st.session_state.telegram_user_id}
            response = requests.post(f"{API_BASE_URL}/generate-plan", json=plan_req_payload)
            response.raise_for_status()
            
            raw_response = response.json().get("raw_plan_response")
            # تلاش برای پیدا کردن JSON در پاسخ
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}')
            if json_start != -1 and json_end != -1:
                plan_str = raw_response[json_start:json_end+1]
                plan_data = json.loads(plan_str)
            else:
                raise json.JSONDecodeError("JSON معتبری در پاسخ یافت نشد.", raw_response, 0)

            st.session_state.plan_data = plan_data
            st.session_state.page = "plan"
            st.rerun()

        except (requests.RequestException, json.JSONDecodeError) as e:
            st.error(f"خطا در ساخت برنامه: {e}")

def display_plan():
    st.balloons()
    st.title("🎉 برنامه تمرینی شما آماده شد!")
    plan_data = st.session_state.plan_data
    st.markdown(f"**خلاصه برنامه:** {plan_data.get('plan_summary', '')}")
    st.markdown("---")
    
    for day_plan in plan_data.get('weekly_plan', []):
        with st.expander(f"**روز {day_plan.get('day')}: {day_plan.get('day_title')}**", expanded=True):
            for exercise in day_plan.get('exercises', []):
                st.markdown(f"- **{exercise.get('name')}**: {exercise.get('sets')} ست × {exercise.get('reps')} تکرار")

def main():
    st.set_page_config(page_title="مربی هوشمند", page_icon="🤖")
    initialize_session_state()
    if st.session_state.page == "form":
        display_smart_form()
    elif st.session_state.page == "plan":
        display_plan()

if __name__ == "__main__":
    main()