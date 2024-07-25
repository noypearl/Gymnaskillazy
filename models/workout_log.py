from dataclasses import dataclass, field
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
    spreadsheet_id: str = ""  # TODO: does that make sense?
    exercises: List[ExerciseUnitLog] = field(default_factory=list)
    custom_exercises: List[ExerciseUnitLog] = field(default_factory=list)
    type: str = ""
    date: str = date_for_exer_log()
