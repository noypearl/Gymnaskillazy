from dataclasses import dataclass
from datetime import datetime


class Model:
    def __repr__(self):
        return f"<{type(self).__name__}({', '.join([f"{kvp[0]}={kvp[1]}" for kvp in self.__dict__.items()])})>"

@dataclass
class StorageObject:
    def __init__(self):
        self.last_updated: datetime
        self.set("last_updated", datetime.now())  # TODO move to time.py

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError(f"Direct assignment of attributes is not allowed. Use setter methods. {self.__class__.__name__}.{name}")
        else:
            super().__setattr__(name, value)

    def set_attr(self, name, value):
        super().__setattr__(name, value)

    def set(self, attribute_name, attribute_value):
        self.set_attr(attribute_name, attribute_value)
        self.set_attr("last_updated", datetime.now())  # TODO move to time.py
