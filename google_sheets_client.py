import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class GoogleSheetsClient:
    def __init__(self, credentials_file, sheet_id):
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.client = self.get_gcloud_connection()

    def get_gcloud_connection(self):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
        return gspread.authorize(credentials)

    def get_current_sheet(self):
        current_month = datetime.now().strftime('%B')
        return self.client.open_by_key(self.sheet_id).worksheet(current_month)

    def get_exercises(self, lesson_type):
        sheet = self.get_current_sheet()
        if lesson_type == 'strength':
            return sheet.col_values(1)[1:10]  # A2:A10
        else:
            return sheet.col_values(2)[1:10]  # B2:B10
