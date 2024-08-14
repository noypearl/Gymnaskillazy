import json

from utilities.filesystem_client import FilesystemClient
from utilities.time import now_for_logs


class LoggerClient:
    def __init__(self, output_file_path: str):
        self.output_file_path = output_file_path

    def log(self, message):
        return  # because IO disturbs the async
        if not isinstance(message, str):
            message = json.dumps(message)
        message = f"[{now_for_logs()}] {message}\n"
        FilesystemClient.write_to_file(self.output_file_path, message)
