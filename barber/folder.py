import os
from glob import glob
from pathlib import Path

class Folder:
    def __init__(self, url:Path):
        self.path = path

    def images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from path.iterdir()
            else:
                yield file

class Collection:
    def __init__(self):
        self.folders = {}

    def add_source(self, name:str, pattern:str):
        pattern = os.path.expanduser(pattern)
        self.folders[name] = list(Path(p) for p in glob(pattern))
        print(list(Path(p) for p in glob(pattern)))
