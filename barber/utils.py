import os
from pathlib import Path
import logging
import toml

fmt = "%(levelname)s:%(asctime).19s: %(message)s"
logging.basicConfig(format=fmt)
logger = logging.getLogger("barber")
if os.environ.get("BARBER_DEBUG"):
    logger.setLevel("DEBUG")
    logger.debug("Log level set to debug")

cfg = {}


def load_config(path):
    cfg.update(toml.load(path.open()))
    return cfg
