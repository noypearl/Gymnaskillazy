import json
import ast
from datetime import datetime
from typing import Union


class LoggerClient:
    def __init__(self, output_file_path: str):
        self.output_file_path = output_file_path

    def log(self, message):
        with open(self.output_file_path, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")

    def log_json(self, message: Union[str,list,dict]):
        serialized = json.dumps(message)
        self.log(serialized)
