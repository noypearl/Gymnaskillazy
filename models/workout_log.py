from dataclasses import dataclass
from typing import List

from utilities.time import date_for_exer_log, time_for_exer_log


@dataclass
class ExerciseUnitLog:
    type: str
    rep_sec: str = ""
    time: str = time_for_exer_log()
    variation: str = ""
    notes: List[str] = None


@dataclass
class WorkoutLog:
    exercises: List[ExerciseUnitLog]
    type: str = ""
    date: str = date_for_exer_log()
