from models import StorageObject
from models.workout_log import WorkoutLog, ExerciseOrder


class UserSession(StorageObject):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.workout_log = WorkoutLog()
        self.previous_exercise_records = {}
        self.exercise_order = ExerciseOrder.DEFAULT
        self.current_exercise = None
