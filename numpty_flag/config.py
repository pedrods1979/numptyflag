import json
from pathlib import Path
from typing import Optional, Union

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_config(path: Optional[Union[str, Path]] = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        return json.load(f)
