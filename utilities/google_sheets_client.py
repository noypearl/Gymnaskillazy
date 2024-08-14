from typing import Optional

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utilities.constants import GENERAL_SHEET, USERS_SHEET, CURRENT_COL, EXERCISE_SHEET, QUESTIONS_COL, TRAINERS_COL, \
    EXERCISE_ID_COL, LOG_SHEET
from models.session import UserSession
from models.workout_log import WorkoutLog, ExerciseUnitLog
from utilities.collections import filter_list_of_dicts_by_kv, uniquify, get_all_values_of_k, filter_cell_list_by_value, \
    get_most_recent_record, is_empty, filter_out_empty_members, neutralize_str
from utilities.time import time_for_exer_log


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
        try:
            return self.client.open_by_key(sheet_id)
        except Exception as e:
            # TODO DEBUG: find out what exception is raised when no doc by this id
            print("oops")
            return


    def get_main_doc_sheet(self, sheet_name):
        return self.main_doc.worksheet(sheet_name)

    def get_exercise_list_by_type(self, workout_type):
        sheet = self.get_main_doc_sheet(EXERCISE_SHEET)
        all_exercises = sheet.get_all_records()
        filtered_exercises = filter_list_of_dicts_by_kv(all_exercises, CURRENT_COL, workout_type)
        exercise_list = get_all_values_of_k(filtered_exercises, EXERCISE_ID_COL)
        return exercise_list

    def get_exercise_last_log(self, user_id: int, exercise: ExerciseUnitLog) -> Optional[ExerciseUnitLog]:
        user_sheet_doc = self.get_user_doc_by_user_id(user_id)
        if user_sheet_doc is None:
            return
        log_sheet = user_sheet_doc.worksheet("Full Workout Log")
        exercise_column_number = self.get_column_number(log_sheet, "Exercise")
        existing_log_for_exercise_type = log_sheet.find(exercise.type, in_column=exercise_column_number)
        if existing_log_for_exercise_type is None:
            return
        past_logs_for_exercise = log_sheet.findall(query=exercise.type, in_column=exercise_column_number)
        last_log_of_exercise = get_most_recent_record(past_logs_for_exercise)
        row_for_last_log = self.get_exercise_row_as_dict_by_cell(log_sheet, last_log_of_exercise.row)
        return ExerciseUnitLog(
            time=row_for_last_log.get("time"),
            type=row_for_last_log.get("exercise"),
            variation=row_for_last_log.get("variation"),
            level=row_for_last_log.get("level"),
            rep_sec=row_for_last_log.get("rep/sec"),
            notes=row_for_last_log.get("notes")
        )

    def get_exercise_variation_list(self, exercise_type):
        exercise_sheet = self.main_doc.worksheet(exercise_type)
        variation_column_number = self.get_column_number(exercise_sheet, "Variation/Level")
        return filter_out_empty_members(exercise_sheet.col_values(variation_column_number))[1:]

    def get_exercise_variation_level_list(self, exercise_type, variation_name):
        exercise_sheet = self.main_doc.worksheet(exercise_type)
        variation_column_header = exercise_sheet.find(variation_name, in_row=1)
        return filter_out_empty_members(exercise_sheet.col_values(variation_column_header.col))

    def get_column_number(self, sheet, column_header: str):
        title_cell = sheet.find(column_header, case_sensitive=False)
        if title_cell is None:
            raise Exception(f"Column {column_header} not found")
        return title_cell.col

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

    def log_workout(self, session: UserSession):
        user_sheet_id = self.get_user_sheet_doc_id_by_user_id(session.user_id)
        user_sheet_doc = self.get_doc(user_sheet_id)
        if user_sheet_doc is None:
            user_sheet_doc = self.create_user_sheet_doc(session.user_id)
        log_sheet = user_sheet_doc.worksheet(LOG_SHEET)
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
                x.notes
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

