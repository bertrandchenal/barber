from pathlib import Path

import toml


cfg = {}


def load_config(path):
    cfg.update(toml.load(path.open()))
    return cfg
