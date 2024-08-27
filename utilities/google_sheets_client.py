from typing import Optional

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from models.session import UserSession
from models.workout_log import WorkoutLog, ExerciseUnitLog
from utilities.collections import uniquify, get_most_recent_record, \
    filter_out_empty_members, neutralize_str, list_to_str, neutralize_list, is_empty
from utilities.constants import USERS_SHEET, PROJECT_SHEET, PERMITTED_USERS_COL, \
    USER_DATA_SHEET, USER_LOG_SHEET, EVEN_MONTH_COL, ODD_MONTH_COL, EXECUTION_DIFFICULTY_HEADER, PROJECT_COL
from utilities.time import is_even_month


class GoogleSheetsClient:
    def __init__(self, credentials_file, main_sheet_id, user_template_sheet_id, user_log_folder_id, storage):
        self.credentials_file = credentials_file
        self.client = self.get_gcloud_connection()
        self.main_doc = self.get_doc(main_sheet_id)
        self.user_template_doc = self.get_doc(user_template_sheet_id)
        self.user_log_folder_id = user_log_folder_id
        self.storage = storage

    def get_gcloud_connection(self):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
        return gspread.authorize(credentials)

    def get_permitted_user_emails(self):
        users_sheet = self.get_main_doc_sheet(USERS_SHEET)
        permitted_users_column_number = self.get_column_number(users_sheet, PERMITTED_USERS_COL)
        return neutralize_list(users_sheet.col_values(permitted_users_column_number)[1:])

    def get_doc(self, sheet_id):
        doc = self.client.open_by_key(sheet_id)
        if doc is None:
            raise Exception("No sheet doc by provided ID")
        return doc

    def get_main_doc_sheet(self, sheet_name):
        return self.main_doc.worksheet(sheet_name)

    def get_user_config(self, user_id):
        user_sheet_doc = self.get_user_doc_by_user_id(user_id)
        user_data_sheet = user_sheet_doc.worksheet(USER_DATA_SHEET)
        headers = [neutralize_str(h) for h in user_data_sheet.col_values(1)]
        col = user_data_sheet.col_values(2)
        result = {}
        for h in range(len(headers)):
            head = headers[h]
            if h >= len(col):
                result[head] = None
            else:
                result[head] = col[h]
        return result

    def get_exercise_last_log(self, user_id: int, exercise_type: str) -> Optional[ExerciseUnitLog]:
        user_sheet_doc = self.get_user_doc_by_user_id(user_id)
        if user_sheet_doc is None:
            return
        log_sheet = user_sheet_doc.worksheet(USER_LOG_SHEET)
        exercise_column_number = self.get_column_number(log_sheet, PROJECT_COL)
        existing_log_for_exercise_type = log_sheet.find(exercise_type, in_column=exercise_column_number)
        if existing_log_for_exercise_type is None:
            return
        past_logs_for_exercise = log_sheet.findall(query=exercise_type, in_column=exercise_column_number)
        last_log_of_exercise = get_most_recent_record(past_logs_for_exercise)
        row_for_last_log = self.get_exercise_row_as_dict_by_cell(log_sheet, last_log_of_exercise.row)
        return ExerciseUnitLog(
            time=row_for_last_log.get("time"),
            type=row_for_last_log.get("project"),
            variation=row_for_last_log.get("execution"),
            level=row_for_last_log.get("difficulty"),
            rep_sec=row_for_last_log.get("rep/sec"),
            notes=row_for_last_log.get("notes")
        )

    def get_exercise_variation_list(self, exercise_type):
        print("get_exercise_variation_list()")
        if self.storage._project_definitions.get(exercise_type) is None:
            exercise_sheet = self.main_doc.worksheet(exercise_type)
            variation_column_number = self.get_column_number(exercise_sheet, EXECUTION_DIFFICULTY_HEADER)
            execution_list = filter_out_empty_members(exercise_sheet.col_values(variation_column_number))[1:]
            self.storage._project_definitions[exercise_type] = {}
            for execution in execution_list:
                self.storage._project_definitions[exercise_type][execution] = []
        return list(self.storage._project_definitions[exercise_type].keys())

    def get_exercise_variation_level_list(self, exercise_type, variation_name):
        print("get_exercise_variation_level_list()")
        if is_empty(self.storage._project_definitions.get(exercise_type)):
            self.get_exercise_variation_list(exercise_type)
        if is_empty(self.storage._project_definitions.get(exercise_type).get(variation_name)):
            exercise_sheet = self.main_doc.worksheet(exercise_type)
            variation_column_header = exercise_sheet.find(variation_name, in_row=1)
            self.storage._project_definitions[exercise_type][variation_name] = filter_out_empty_members(exercise_sheet.col_values(variation_column_header.col))
        return self.storage._project_definitions[exercise_type][variation_name]
    def get_column_number(self, sheet, column_header: str):
        title_cell = sheet.find(column_header, case_sensitive=False)
        if title_cell is None:
            raise Exception(f"Column {column_header} not found")
        return title_cell.col

    def load_month_exercises(self):
        print("load_month_exercises()")
        if not is_empty(self.storage.month_exercises):
            return
        sheet = self.get_main_doc_sheet(PROJECT_SHEET)
        is_even = is_even_month()
        if is_even:
            month_col = EVEN_MONTH_COL
        else:
            month_col = ODD_MONTH_COL
        column_number = self.get_column_number(sheet, month_col)
        exercise_types = filter_out_empty_members(uniquify(sheet.col_values(column_number)))
        exercises = {}
        exercise_rows = []
        for typ in exercise_types:
            exercises[typ] = []
            exercise_rows.extend(sheet.findall(typ, in_column=column_number))
        for exercise_cell in exercise_rows:
            exercises[exercise_cell.value].append(sheet.cell(exercise_cell.row, exercise_cell.col-1).value)
        self.storage.month_exercises = exercises

    def create_user_sheet_doc(self, user_id):
        """
        Creates a new sheet for the user and registers it in main/users
        :return: Spreadsheet
        """
        new_user_doc = self.client.copy(
            file_id=self.user_template_doc.id,
            title=user_id,
            folder_id=self.user_log_folder_id
        )
        new_user_doc.share('hilla.sh@gmail.com', perm_type='user', role='writer')  # TODO: share with user
        users_sheet = self.main_doc.worksheet(USERS_SHEET)
        users_sheet.append_row([user_id, new_user_doc.id])
        return new_user_doc

    def get_user_doc_id_by_user_id(self, user_id):
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
        user_doc = self.storage.users[user_id].sheet_doc
        if user_doc is None:
            self.storage.users[user_id].set("sheet_doc", self.get_doc(self.get_user_doc_id_by_user_id(user_id)))
            user_doc = self.storage.users[user_id].sheet_doc
        return user_doc

    def update_settings(self, user_doc, setting_name, new_value):
        user_data_sheet = user_doc.worksheet(USER_DATA_SHEET)
        setting_location = user_data_sheet.find(setting_name, in_column=1, case_sensitive=False)
        user_data_sheet.update_cell(setting_location.row, setting_location.col+1, new_value)

    def log_workout(self, session: UserSession):
        user_sheet_doc = self.get_user_doc_by_user_id(session.user_id)
        log_sheet = user_sheet_doc.worksheet(USER_LOG_SHEET)
        rows = self.parse_log_to_rows(session.workout_log)
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
                x.level,
                x.rep_sec,
                list_to_str(x.notes)
            ])
        return logs_list

    def get_exercise_row_as_dict_by_cell(self, worksheet, cell_row) -> dict:
        # for user exercise log
        headers = [neutralize_str(h) for h in worksheet.row_values(1)]
        row = worksheet.row_values(cell_row)
        result = {}
        for h in range(len(headers)):
            head = headers[h]
            if h >= len(row):
                result[head] = None
            else:
                result[head] = row[h]
        return result
