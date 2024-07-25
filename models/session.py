from dataclasses import dataclass

from models.workout_log import WorkoutLog, ExerciseUnitLog

@dataclass
class UserSession:
    user_id: int
    workout_log: WorkoutLog = None
    current_exercise: ExerciseUnitLog = None
