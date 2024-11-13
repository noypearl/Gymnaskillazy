from dataclasses import dataclass

from gspread import Spreadsheet

from models import StorageObject
from models.session import UserSession


@dataclass
class UserConfig(StorageObject):
    def __init__(self, email=None, log_order=None):
        super().__init__()
        self.set("email", email)

    @property
    def email(self):
        return self._attributes.get("email")

    @email.setter
    def email(self, new_value: str):
        self.set("email", new_value)

@dataclass
class User(StorageObject):
    id: int
    _session: UserSession
    _config: UserConfig
    _sheet_doc: Spreadsheet = None

    def __init__(self, user_id):
        super().__init__()
        self.set_attr("id", user_id)
        self.session = UserSession(user_id)
        self.config = UserConfig()

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config: UserConfig):
        self.set_attr("_config", config)

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, session: UserSession):
        self.set_attr("_session" ,session)

    @property
    def sheet_doc(self):
        return self._sheet_doc

    @sheet_doc.setter
    def sheet_doc(self, sheet_doc: Spreadsheet):
        self.set("_sheet_doc", sheet_doc)
