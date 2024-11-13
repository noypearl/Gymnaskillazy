from datetime import datetime, timedelta

from models.session import UserSession
from models.user import UserConfig
from utilities.collections import is_empty
from utilities.config import (GOOGLE_SHEETS_CREDENTIALS_FILE,
                              GOOGLE_SHEETS_MAIN_DOC_ID,
                              GOOGLE_SHEETS_USER_LOG_FOLDER_ID,
                              GOOGLE_SHEETS_USER_TEMPLATE_DOC_ID)
from utilities.google_sheets_client import GoogleSheetsClient


class Storage:
    def __init__(self):
        self._users = {}
        self._month_projects = {}
        self.__google_sheets_client = GoogleSheetsClient(
            credentials_file=GOOGLE_SHEETS_CREDENTIALS_FILE,
            main_sheet_id=GOOGLE_SHEETS_MAIN_DOC_ID, 
            user_template_sheet_id=GOOGLE_SHEETS_USER_TEMPLATE_DOC_ID,
            user_log_folder_id=GOOGLE_SHEETS_USER_LOG_FOLDER_ID,
        )


    @property
    def permitted_email_list(self):
        return self.__google_sheets_client.get_permitted_user_emails()

    @property
    def users(self):
        return self._users

    @property
    def month_projects(self):
        if is_empty(self._month_projects):
            self.month_projects = self.__google_sheets_client.get_month_projects()
            self.load_project_definitions()
        return self._month_projects

    @month_projects.setter
    def month_projects(self, month_projects):
        self._month_projects = month_projects

    def get_project_last_log(self, user_id, project_type):
        self.__google_sheets_client.get_project_last_log(user_id, project_type)

    def get_executions_by_project(self, project_type: str):
        return list(self.month_projects[project_type].keys())

    def load_project_definitions(self):
        print("get_exercise_variation_list()")
        for project_type in self.month_projects.keys():
            if self.month_projects.get(project_type) is None:
                self.month_projects[project_type] = self.__google_sheets_client.get_project_execution_variation_list(project_type)

    def get_session(self, user_id):
        return self.users[user_id].session

    def get_user_doc(self, user_id):
        user_doc = self.users[user_id].sheet_doc
        if user_doc is None:
            user_doc = self.__google_sheets_client.get_user_doc_by_user_id(user_id)
            self.users[user_id].set("sheet_doc", user_doc)
        return user_doc

    def refresh_user_data(self, user_id):
        if datetime.fromtimestamp(self.users[user_id].last_updated) < datetime.now() - timedelta(weeks=1):
            self.load_user_data(user_id)


    def update_user_config(self, user_id, setting_name, setting_value):
        user_doc = self.users[user_id].sheet_doc
        if user_doc is None:
            user_doc = self.users[user_id].sheet_doc = self.get_user_doc(user_id)
        self.__google_sheets_client.update_user_config(user_doc, setting_name, setting_value)
        self.users[user_id].config.set(setting_name, setting_value)

    def load_user_data(self, user_id):
        self.users[user_id].config = UserConfig(**self.__google_sheets_client.get_user_config(user_id))

    def log_workout(self, session: UserSession):
        self.__google_sheets_client.log_workout(session)
