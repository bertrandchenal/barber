import io
import os
import uuid
from datetime import datetime
from hashlib import md5
from glob import glob
from pathlib import Path

from nagra import Transaction, Table
from PIL import Image as PILImage, ImageOps

from barber.utils import logger, init_db


DISK_MIN_FILE_SIZE = 100 * 1024
OK_EXT = (".png", ".jpg", ".jpeg")
DIGEST_HEAD = 4 * 1024


def digest(content):
    return md5(content).hexdigest()


class Image:
    __slots__ = ["path", "digest", "db_uri"]
    _by_digest = {}

    def __init__(self, path: Path, db_uri: Path):
        self.path = path
        self.digest = digest(path.open("rb").read(DIGEST_HEAD))
        self.db_uri = db_uri
        Image._by_digest[self.digest] = self

    @classmethod
    def get(cls, digest: str):
        return cls._by_digest[digest]

    def thumb(self):
        with Transaction(self.db_uri):
            thumb_table = Table.get("thumb")
            # Return from cache if key exists
            select = thumb_table.select("content").where("(= digest {})")
            if record := select.execute(self.digest).fetchone():
                (content,) = record
                return io.BytesIO(content)
            # Compute thumb
            logger.info("Generate thumbnail for %s", self.path)
            im = PILImage.open(self.path)
            im.thumbnail((640, 480))  # im.draft('RGB',(320, 240))
            ImageOps.exif_transpose(im, in_place=True)
            thumb = io.BytesIO()
            fmt = "PNG" if self.path.suffix.lower() == ".png" else "JPEG"
            im.save(thumb, format=fmt)
            thumb.seek(0)
            # Save to cache and return
            thumb_table.upsert().execute(
                self.digest,
                thumb.getvalue(),
                datetime.now(),
            )
            return thumb

    def full(self):
        return self.path.open("rb")

    def flip_star(self):
        return True


class Folder:
    def __init__(self, path: Path):
        self.path = path
        db_uri = f"sqlite://{self.path}/.thumbs.db"
        init_db(db_uri)
        self.images = [Image(p, db_uri) for p in sorted(self._images())]
        logger.info("Added folder '%s' wih %s images", self.path, len(self.images))

    def _images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from (f for f in file.iterdir() if self.is_image(f))
            elif self.is_image(file):
                yield file

    @staticmethod
    def is_image(f):
        return f.is_file() and f.suffix.lower() in OK_EXT


class Collection:
    def __init__(self):
        self.folders = {}

    def add_source(self, name: str, pattern: str):
        pattern = os.path.expanduser(pattern)
        if "*" in pattern:
            folders = list(Folder(Path(p)) for p in sorted(glob(pattern)))
        else:
            folders = [Folder(Path(pattern))]
        self.folders[name] = folders
