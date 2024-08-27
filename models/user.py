from dataclasses import dataclass

from gspread import Spreadsheet

from models import StorageObject
from models.session import UserSession


@dataclass
class User(StorageObject):
    id: int
    _session: UserSession
    config: dict = None
    sheet_doc: Spreadsheet = None

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self._session = UserSession(user_id)

    @property
    def session(self):
        if self._session is None:
            self._session = UserSession(self.user_id)
        return self._session
