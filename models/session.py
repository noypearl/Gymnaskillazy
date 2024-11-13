from dataclasses import dataclass

from models import StorageObject
from models.workout_log import ExerciseOrder, ExerciseUnitLog, WorkoutLog


@dataclass
class UserSession(StorageObject):
    user_id: int
    workout_log: WorkoutLog
    previous_project_records: dict
    project_order: ExerciseOrder
    current_project: ExerciseUnitLog


    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.workout_log = WorkoutLog()
        self.previous_project_records = {}
        self.project_order = ExerciseOrder.DEFAULT
        self.current_project = None
