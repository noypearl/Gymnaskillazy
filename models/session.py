from dataclasses import dataclass, field

from models.workout_log import WorkoutLog, ExerciseUnitLog

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.workout_log = WorkoutLog()
        self.current_exercise = None
