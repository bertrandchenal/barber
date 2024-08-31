import os
import logging
from pathlib import Path
from functools import lru_cache

import toml
from nagra import Transaction, Schema

HERE = Path(__file__).parent

# Define schema
Schema.default.load_toml(HERE / 'schema.toml')

# Setup logging
fmt = "%(levelname)s:%(asctime).19s: %(message)s"
logging.basicConfig(format=fmt)
logger = logging.getLogger("barber")
logger.setLevel("INFO")
if os.environ.get("BARBER_DEBUG"):
    logger.setLevel("DEBUG")
    logger.debug("Log level set to debug")


# Init empty config
cfg = {}


def init_db(db_uri):
    with Transaction(db_uri):
        Schema.default.create_tables()


@lru_cache
def config():
    path = Path(os.environ.get("BARBER_TOML", "./barber.toml"))
    cfg.update(toml.load(path.open()))
    return cfg
