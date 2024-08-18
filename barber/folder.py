import io
import os
import uuid
from hashlib import md5
from glob import glob
from pathlib import Path

from diskcache import Cache
from PIL import Image as PILImage, ImageOps

from barber.utils import logger


DISK_MIN_FILE_SIZE = 100 * 1024
OK_EXT = (".png", ".jpg", ".jpeg")
DIGEST_HEAD = 4 * 1024


def digest(content):
    return md5(content).hexdigest()


class Image:
    __slots__ = ["path", "digest", "cache_dir"]
    _by_digest = {}

    def __init__(self, path: Path, cache_dir: Path):
        self.path = path
        self.digest = digest(path.open("rb").read(DIGEST_HEAD))
        self.cache_dir = cache_dir
        Image._by_digest[self.digest] = self

    @classmethod
    def get(cls, digest: str):
        return cls._by_digest[digest]

    def thumb(self):
        with Cache(self.cache_dir, disk_min_file_size=DISK_MIN_FILE_SIZE) as cache:
            # Return from cache if key exists
            if thumb := cache.get(self.digest):
                return io.BytesIO(thumb)
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
            cache.set(self.digest, thumb.getvalue())
            return thumb

    def full(self):
        return self.path.open("rb")


class Folder:
    def __init__(self, path: Path):
        self.path = path
        cache_dir = path / ".thumbs"
        cache_dir.mkdir(exist_ok=True)
        self.images = [Image(p, cache_dir=cache_dir) for p in sorted(self._images())]
        logger.info("Added folder '%s' wih %s images", self.path, len(self.images))

    def _images(self):
        for file in self.path.iterdir():
            if file.is_dir():
                yield from (f for f in file.iterdir() if self.is_image(f))
            else:
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
