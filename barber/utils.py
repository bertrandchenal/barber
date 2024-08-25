import os
import logging

import toml
from nagra import Transaction, Schema

# Define schema
schema_toml = """
[thumb]
natural_key = ["digest"]
[thumb.columns]
digest = "str"
content = "blob"
created_at = "timestamp"

[tag]
natural_key = ["digest", "value"]
[tag.columns]
digest = "str"
value = "str"
"""
Schema.default.load_toml(schema_toml)

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


def load_config(path):
    cfg.update(toml.load(path.open()))
    return cfg
