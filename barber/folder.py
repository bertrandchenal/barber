import io
import os
import uuid
from hashlib import md5
from glob import glob
from pathlib import Path

from PIL import Image as PILImage, ImageOps


def digest(content):
    return md5(content).hexdigest()

class Image:
    __slots__ = ["path", "digest", "_thumb"]
    _by_digest = {}

    def __init__(self, path: Path):
        self.path = path
        self.digest = digest(path.open("rb").read(1024))
        self._thumb = None
        Image._by_digest[self.digest] = self

    @classmethod
    def get(cls, digest: str):
        return cls._by_digest[digest]

    def thumb(self):
        if self._thumb is None:
            im = PILImage.open(self.path)
            #im.draft('RGB',(320, 240))
            im.thumbnail((640, 480))
            ImageOps.exif_transpose(im, in_place=True)
            buff = io.BytesIO()
            im.save(buff, format="JPEG")
            self._thumb = buff
        self._thumb.seek(0)
        return self._thumb


class Folder:
    def __init__(self, path: Path):
        self.path = path
        self.images = [Image(p) for p in sorted(self._images())]

    def _images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from (f for f in file.iterdir() if f.is_file())
            else:
                yield file


class Collection:
    def __init__(self):
        self.folders = {}

    def add_source(self, name: str, pattern: str):
        pattern = os.path.expanduser(pattern)
        self.folders[name] = list(Folder(Path(p)) for p in sorted(glob(pattern)))
