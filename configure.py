from pathlib import Path

import yaml

CONFIG = yaml.safe_load(Path("configuration.yml").read_text("UTF-8"))
