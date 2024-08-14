class Model:
    def __repr__(self):
        return f"<{type(self).__name__}({', '.join([f"{kvp[0]}={kvp[1]}" for kvp in self.__dict__.items()])})>"
