import io
import os
from bisect import bisect_left, bisect_right
from datetime import datetime
from hashlib import md5
from glob import glob
from pathlib import Path
from functools import lru_cache

from nagra import Transaction, Table
from PIL import Image as PILImage, ImageOps

from barber.utils import logger, init_db, config

cfg = config()
DISK_MIN_FILE_SIZE = 100 * 1024
OK_EXT = (".png", ".jpg", ".jpeg")
DIGEST_HEAD = 4 * 1024
THUMB_SIZE = 640


def digest(content):
    return md5(content).hexdigest()


class Tags:

    _tags = None

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
        logger.info("Found folder '%s' wih %s images", self.path, len(self.images))

    def _images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from (f for f in file.iterdir() if self.is_image(f))
            elif self.is_image(file):
                yield file

    @staticmethod
    def is_image(f):
        return f.is_file() and f.suffix.lower() in OK_EXT

    def upload(self, minio_client):
        sizes = cfg['destination']['sizes']
        root = cfg['destination']['root']
        name = self.path.name
        on_server = list(minio_client.ls(f'{root}/{name}'))
        # on_server looks like ['2019.01/DSCF6630@1600.JPG']
        for image in self.images:
            if not image.starred:
                continue
            for size in sizes:
                dest = f'{name}/{image.path.stem}@{size}{image.path.suffix}'
                # dest_path = rel_dir / f'{path.stem}@{size}{path.suffix}'
                if str(dest) in on_server:
                    continue
                content = image.resize(size)
                logger.info("Upload to %s", dest)
                minio_client.send(content, Path('images') / dest)


class Collection:
    def __init__(self):
        self._sources = {}

    def add_source(self, name: str, pattern: str):
        self._sources[name] = pattern

    @property
    @lru_cache
    def folders(self):
        res = {}
        for name, pattern in self._sources.items():
            pattern = os.path.expanduser(pattern)
            if "*" in pattern:
                folders = list(Folder(Path(p)) for p in sorted(glob(pattern)))
            else:
                folders = [Folder(Path(pattern))]
            res[name] = folders
        return res


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
            content = self.resize(THUMB_SIZE)
            # Save to cache and return
            thumb_table.upsert().execute(
                self.digest,
                content,
                datetime.now(),
            )
            return io.BytesIO(content)

    def __lt__(self, other):
        return self.path < other.path

    @property
    @lru_cache
    def next(self):
        pos = bisect_right(self.folder.images, self)
        return self.folder.images[pos]

    @property
    @lru_cache
    def prev(self):
        pos = bisect_left(self.folder.images, self)
        return self.folder.images[pos]

    def resize(self, max_side):
        logger.info("Generate thumbnail for %s", self.path)
        im = PILImage.open(self.path)
        try:
            im.thumbnail((max_side, max_side))  # im.draft('RGB',(320, 240))
        except OSError:
            logger.exception(f"Unable to resize {self.path}")
        ImageOps.exif_transpose(im, in_place=True)
        thumb = io.BytesIO()
        fmt = "PNG" if self.path.suffix.lower() == ".png" else "JPEG"
        im.save(thumb, format=fmt)
        thumb.seek(0)
        return thumb.getvalue()

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
