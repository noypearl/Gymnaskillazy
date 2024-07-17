class FilesystemClient:
    def __init__(self):
        pass

    @staticmethod
    def read_file(path: str) -> str:
        with open(path, 'r') as f:
            return f.read()

    def read_json(self, path):
        content_str = self.read_file(path)
        return json.loads(content_str)

    @staticmethod
    def write_file(path, content):
        with open(path, 'w') as f:
            f.write(content)

    def write_json(self, path: str, content: Union[str,list,dict]):
        content_str = json.dumps(content)
        self.write_file(path, content_str)