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


class Tags:

    _tags = None

    @classmethod
    def __init__(self, folder):
        self.folder = folder
        with Transaction(folder.db_uri):
            rows = Table.get("tag").select("digest", "value")
        self._tags = set(rows)

    def add(self, digest, value):
        self._tags.add((digest, value))
        with Transaction(self.folder.db_uri):
            Table.get("tag").upsert("digest", "value").execute(digest, value)

    def rm(self, digest, value):
        self._tags.discard((digest, value))
        with Transaction(self.folder.db_uri):
            Table.get("tag").delete().where(
                "(= digest {})",
                "(= value {})",
            ).execute(digest, value)

    def __contains__(self, key):
        return key in self._tags


class Folder:
    def __init__(self, path: Path):
        self.path = path
        self.db_uri = f"sqlite://{self.path}/.thumbs.db"
        init_db(self.db_uri)
        self.tags = Tags(self)
        self.images = [Image(p, self) for p in sorted(self._images())]
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


class Image:
    __slots__ = ["path", "digest", "folder"]
    _by_digest = {}

    def __init__(self, path: Path, folder: Folder):
        self.path = path
        self.digest = digest(path.open("rb").read(DIGEST_HEAD))
        self.folder = folder
        Image._by_digest[self.digest] = self

    @classmethod
    def get(cls, digest: str):
        return cls._by_digest[digest]

    def thumb(self):
        with Transaction(self.folder.db_uri):
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

    @property
    def starred(self):
        return (self.digest, "star") in self.folder.tags

    def flip_star(self):
        key = (self.digest, "star")
        if self.starred:
            logger.info("Remove star from %s", self.digest)
            self.folder.tags.rm(*key)
            return False

        logger.info("Add star for %s", self.digest)
        self.folder.tags.add(*key)
        return True

    def full(self):
        return self.path.open("rb")
