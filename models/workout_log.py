import itertools

from utilities.collections import is_empty
from utilities.time import date_for_exer_log, time_for_exer_log


class ExerciseUnitLog:
    id_iter = itertools.count()

    def __init__(self, type: str, time=None, variation=None, level=None, rep_sec=None, notes=None):
        self.idx = next(self.id_iter)
        self.type = type  # exercise type
        self.rep_sec = rep_sec
        self.time = time_for_exer_log() if None else time
        self.variation = variation
        self.level = level
        self.notes = [] if None else notes

    def __repr__(self):
        return f'<ExerciseUnitLog(idx={self.idx}, time={self.time}, type={self.type}, rep_sec={self.rep_sec}, variation={self.variation}, level={self.level}, notes={self.notes})>'

class WorkoutLog:
    def __init__(self, date = None):
        self.spreadsheet_id = None  # TODO: does that make sense?
        self.exercises = []
        self.custom_exercises = []
        self.type = None
        self.date = date_for_exer_log() if None else date

    def __repr__(self):
        return f'<WorkoutLog(date={self.date}, exercises={self.exercises}, custom_exercises={self.custom_exercises}, type={self.type})>'

    def last_exercise_of_same_type(self, exercise: ExerciseUnitLog):
        all_exercise_logs_of_type = self.get_all_exercise_logs_by_exercise_type(exercise.type)
        if min([ex.idx for ex in all_exercise_logs_of_type]) < exercise.idx:
            return self.get_exercise_by_idx(exercise.idx - 1)

    def get_all_exercise_logs_by_exercise_type(self, exercise_name):
        return [ex for ex in self.exercises if ex.type == exercise_name]

    def get_exercise_by_idx(self, idx):
        ex_lookup = [ex for ex in self.exercises if ex.idx == idx]
        if is_empty(ex_lookup):
            raise IndexError(f'No exercise by idx {idx}')
        return ex_lookup[0]