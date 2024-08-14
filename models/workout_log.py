import itertools
from dataclasses import dataclass, field
from typing import List

from models import Model
from utilities.collections import is_empty
from utilities.time import date_for_exer_log, time_for_exer_log


class ExerciseUnitLog(Model):
    id_iter = itertools.count()

    def __init__(self, type: str, time=None, variation=None, level=None, rep_sec=None, notes=None):
        self.id = next(self.id_iter)
        self.type = type
        self.rep_sec = rep_sec
        self.time = time_for_exer_log() if time is None else time
        self.variation = variation
        self.level = level
        self.notes = [] if notes is None else notes

class WorkoutLog(Model):
    def __init__(self, date=None):
        self.exercises = []
        self.custom_exercises = []
        self.type = None
        self.date = date_for_exer_log() if date is None else date

    def exercise_count(self):
        return len(self.exercises)

    def populate_exercises(self, exercise_name_list):
        self.exercises = [ExerciseUnitLog(type=ex_name) for ex_name in exercise_name_list]

    def last_exercise_of_same_type(self, exercise: ExerciseUnitLog):
        all_exercise_logs_of_type = self.get_all_exercise_logs_by_exercise_type(exercise.type)
        if min([ex.id for ex in all_exercise_logs_of_type]) < exercise.id:
            return self.get_exercise_by_id(exercise.id - 1)
        return None

    def get_all_exercise_logs_by_exercise_type(self, exercise_name):
        return [ex for ex in self.exercises if ex.type == exercise_name]

    def get_exercise_by_id(self, id):
        ex_lookup = [ex for ex in self.exercises if ex.id == id]
        if is_empty(ex_lookup):
            raise IndexError(f'No exercise by id {id}')
        return ex_lookup[0]
