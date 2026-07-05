"""Asset/config path resolution that works both from source and from a
PyInstaller-frozen exe, where bundled files are extracted to a temp dir
(sys._MEIPASS) that disappears when the process exits.
"""

import sys
from pathlib import Path


def app_root() -> Path:
    """Directory containing the bundled read-only assets (overlay/, the
    default config.json): the repo root when running from source, or
    PyInstaller's extraction dir when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Where user-editable files (config.json) live: next to the exe when
    frozen, so edits survive between runs -- never inside PyInstaller's
    temp extraction dir, which is wiped on exit."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def overlay_html_uri() -> str:
    return (app_root() / "overlay" / "index.html").as_uri()
