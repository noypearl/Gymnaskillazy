from datetime import datetime, timedelta


class Storage:
    def __init__(self):
        self.users = {}
        self.month_exercises = {}

    def get_session(self, user_id):
        return self.users[user_id].session

    def get_user_doc(self, user_id):
        return self.users[user_id].sheet_doc

    def refresh_user_data(self, user_id):
        if datetime.fromtimestamp(self.users[user_id].last_updated) < datetime.now() - timedelta(weeks=1):
            self.load_user_data(user_id)

    def load_month_exercises(self):
        # read from sheet once every hour
        pass

    def load_user_data(self, user_id):
        pass
