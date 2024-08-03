import os
import uuid
from glob import glob
from pathlib import Path


class Image:
    __slots__ = ["path", "uuid", "thumb"]
    _by_uuid = {}

    def __init__(self, path: Path):
        self.path = path
        self.uuid = uuid.uuid4().hex
        Image._by_uuid[self.uuid] = self

    @classmethod
    def get(cls, uuid: str):
        return cls._by_uuid[uuid]


class Folder:
    def __init__(self, path: Path):
        self.path = path
        self.images = list(Image(p) for p in self._images())

    def _images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from file.iterdir()
            else:
                yield file


class Collection:
    def __init__(self):
        self.folders = {}

    def add_source(self, name: str, pattern: str):
        pattern = os.path.expanduser(pattern)
        self.folders[name] = list(Folder(Path(p)) for p in sorted(glob(pattern)))
