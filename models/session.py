from models.workout_log import WorkoutLog


class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.spreadsheet_doc = None
        self.workout_log = WorkoutLog()
        self.current_exercise = None

    def set_spreadsheet_doc(self, spreadsheet_doc):
        self.spreadsheet_doc = spreadsheet_doc
