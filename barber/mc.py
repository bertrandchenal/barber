import json
from io import BytesIO
from pathlib import Path

from minio import Minio

from barber.utils import logger


class MinioClient:

    def __init__(self, host_alias):
        cfg = json.load(Path('~/.mc/config.json').expanduser().open())
        info = cfg['hosts'][host_alias]
        host = info['url'].split('//', 1)[1]
        self.client = Minio(
            host,
            access_key=info['accessKey'],
            secret_key=info['secretKey'],
        )

    def ls(self, path):
        # List all object paths in bucket that begin with path root
        bucket, prefix = self.bsplit(path)
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        for obj in objects:
            yield obj.object_name

    def send(self, content, remote_path):
        bucket, name = self.bsplit(remote_path)
        ext = Path(name).suffix
        if not ext.lower() in ('.jpg', '.jpeg'):
            raise ValueError(f'File extension "{ext}" not supported')
        content_type = 'image/jpeg'
        self.client.put_object(
            bucket,
            name,
            BytesIO(content),
            length=len(content),
            content_type=content_type,
        )


    def bsplit(self, name):
        '''
        split name like bucket_name/ham/spam into bucket_name and ham/spam
        '''
        bucket, *tail = Path(name).parts
        return bucket, '/'.join(tail)
