import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

from constants import GENERAL_SHEET, USERS_SHEET, CURRENT_COL, EXERCISE_SHEET, QUESTIONS_COL, TRAINERS_COL, \
    EXERCISE_ID_COL, LOG_SHEET
from models.workout_log import WorkoutLog
from utilities.collections import filter_list_of_dicts_by_kv, uniquify, get_all_values_of_k


class GoogleSheetsClient:
    def __init__(self, credentials_file, main_sheet_id, user_template_sheet_id, user_log_folder_id):
        self.credentials_file = credentials_file
        self.client = self.get_gcloud_connection()
        self.main_doc = self.get_doc(main_sheet_id)
        self.user_template_doc = self.get_doc(user_template_sheet_id)
        self.user_log_folder_id = user_log_folder_id

    def get_gcloud_connection(self):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
        return gspread.authorize(credentials)

    def get_doc(self, sheet_id):
        return self.client.open_by_key(sheet_id)

    def get_main_doc_sheet(self, sheet_name):
        return self.main_doc.worksheet(sheet_name)

    def get_exercise_list_by_type(self, workout_type):
        sheet = self.get_main_doc_sheet(EXERCISE_SHEET)
        all_exercises = sheet.get_all_records()
        filtered_exercises = filter_list_of_dicts_by_kv(all_exercises, CURRENT_COL, workout_type)
        exercise_list = get_all_values_of_k(filtered_exercises, EXERCISE_ID_COL)
        return exercise_list

    def get_additional_questions(self):
        return self.get_general_sheet_list(QUESTIONS_COL)

    def get_trainer_list(self):
        return self.get_general_sheet_list(TRAINERS_COL)

    def get_workout_type_list(self):
        sheet = self.get_main_doc_sheet(EXERCISE_SHEET)
        column_number = sheet.find(CURRENT_COL).col
        return uniquify(sheet.col_values(column_number)[1:])

    def get_general_sheet_list(self, column_name):
        sheet = self.get_main_doc_sheet(GENERAL_SHEET)
        column_number = sheet.find(column_name).col
        return uniquify(sheet.col_values(column_number)[1:])

    def create_user_sheet_doc(self, user_id):
        """
        Creates a new sheet for the user and registers it in main/users
        :return: Spreadsheet
        """
        print("breakpoint")
        new_user_doc = self.client.copy(
            file_id=self.user_template_doc.id,
            title=user_id,
            folder_id=self.user_log_folder_id
        )
        new_user_doc.share('hilla.sh@gmail.com', perm_type='user', role='writer')
        users_sheet = self.main_doc.worksheet(USERS_SHEET)
        users_sheet.append_row([user_id, new_user_doc.id])
        return new_user_doc

    def get_user_sheet_doc_id_by_user_id(self, user_id):
        users_sheet = self.main_doc.worksheet(USERS_SHEET)
        user_id_str = str(user_id)
        user_id_cell = users_sheet.find(user_id_str)
        if not user_id_cell:
            new_user_doc = self.create_user_sheet_doc(user_id)
            users_sheet.append_row([user_id, new_user_doc.id])
            user_sheet_id_cell = users_sheet.find(new_user_doc.id)
        else:
            user_sheet_id_cell = users_sheet.cell(user_id_cell.row, user_id_cell.col + 1)
        return user_sheet_id_cell.value

    def get_user_doc_by_user_id(self, user_id):
        user_doc_id = self.get_user_sheet_doc_id_by_user_id(user_id)
        return self.get_doc(user_doc_id)

    def log_workout(self, user_id, logs_object: WorkoutLog):
        user_sheet_id = self.get_user_sheet_doc_id_by_user_id(user_id)
        user_sheet_doc = self.get_doc(user_sheet_id)
        if user_sheet_doc is None:
            user_sheet_doc = self.create_user_sheet_doc(user_id)
        log_sheet = user_sheet_doc.worksheet(LOG_SHEET)
        rows = self.parse_log_to_rows(logs_object)
        log_sheet.append_rows(rows)

    def parse_log_to_rows(self, logs_object: WorkoutLog):
        logs_list = []
        sorted_exercises = sorted(logs_object.exercises, key=lambda ex: ex.time)
        for x in sorted_exercises:
            logs_list.append([
                logs_object.date,
                x.time,
                x.type,
                x.variation,
                x.rep_sec,
                x.notes
            ])
        return logs_list
