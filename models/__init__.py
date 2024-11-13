from dataclasses import asdict, dataclass
from datetime import datetime


class Model:
    def __repr__(self):
        return f"<{type(self).__name__}({', '.join([f"{kvp[0]}={kvp[1]}" for kvp in self.__dict__.items()])})>"

@dataclass
class StorageObject:
    def __init__(self):
        self._attributes = {}
        self._attributes["__last_updated"] = datetime.now()

    def __setattr__(self, name, value):
        # Allow initialization of internal attributes
        if name.startswith("_") or name not in self._attributes:
            super().__setattr__(name, value)
        else:
            # Route attribute assignment through the `set` method
            self.set(name, value)

    def set_attr(self, name, value):
        """Allow setting attributes bypassing __setattr__ restrictions."""
        super().__setattr__(name, value)

    def set(self, attribute_name, attribute_value):
        self._attributes[attribute_name] = attribute_value
        self._attributes["__last_updated"] = datetime.now()  # TODO move to time.py

    @property
    def dict(self):
        return {k:v for k,v in self._attributes.items() if not k.startswith("__")}
