class FilesystemClient:

    @staticmethod
    def write_to_file(path, content):
        with open(path, 'a') as f:
            f.write(content)
