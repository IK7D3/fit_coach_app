# initialize_session.py
import streamlit as st

class SessionManager:
    def __init__(self):
        if 'initialized' not in st.session_state:
            self.initialized = True
            self.query_params = st.query_params
            self.user_id = self.query_params.get("user_id")
            self.first_name = self.query_params.get("first_name")
            self.telegram_user_id = int(self.user_id) if self.user_id else 99999
            self.first_name = self.first_name or "کاربر تستی"
            self.gender_input = None
            self.height_input = 170
            self.current_weight_input = 70.0
            self.target_weight_input = 80.0
            self.messages = []
            self.plan_received = False
            self.form_step = 2

    def get_initialized(self):
        return self.initialized

    def set_initialized(self, value):
        self.initialized = value

    def get_query_params(self):
        return self.query_params

    def set_query_params(self, value):
        self.query_params = value

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, value):
        self.user_id = value

    def get_first_name(self):
        return self.first_name

    def set_first_name(self, value):
        self.first_name = value

    def get_telegram_user_id(self):
        return self.telegram_user_id

    def set_telegram_user_id(self, value):
        self.telegram_user_id = value

    def get_gender_input(self):
        return self.gender_input

    def set_gender_input(self, value):
        self.gender_input = value

    def get_height_input(self):
        return self.height_input

    def set_height_input(self, value):
        self.height_input = value

    def get_current_weight_input(self):
        return self.current_weight_input

    def set_current_weight_input(self, value):
        self.current_weight_input = value

    def get_target_weight_input(self):
        return self.target_weight_input

    def set_target_weight_input(self, value):
        self.target_weight_input = value

    def get_messages(self):
        return self.messages

    def set_messages(self, value):
        self.messages = value

    def get_plan_received(self):
        return self.plan_received

    def set_plan_received(self, value):
        self.plan_received = value

    def get_form_step(self):
        return self.form_step

    def set_form_step(self, value):
        self.form_step = value



