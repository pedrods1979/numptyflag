import json
import shutil
from pathlib import Path
from typing import Optional, Union

from .paths import app_root, user_data_dir


def _default_config_path() -> Path:
    user_path = user_data_dir() / "config.json"
    if not user_path.exists():
        bundled = app_root() / "config.json"
        if bundled.exists() and bundled != user_path:
            shutil.copy(bundled, user_path)
    return user_path


def load_config(path: Optional[Union[str, Path]] = None) -> dict:
    path = Path(path) if path else _default_config_path()
    with open(path) as f:
        return json.load(f)
