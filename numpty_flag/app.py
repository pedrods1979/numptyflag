"""Single-process entry point: runs the collector/engine/websocket server on
a background thread and the overlay window on the main thread (GUI toolkits
need the main thread on Windows). This is what gets packaged into
NumptyFlag.exe by PyInstaller -- one process, one window, no manual
terminal juggling.
"""

import asyncio
import logging
import threading

import webview

from .config import load_config
from .main import run_backend
from .paths import overlay_html_uri

logging.basicConfig(level=logging.INFO)


def _run_backend_thread(config: dict) -> None:
    asyncio.run(run_backend(config))


def main() -> None:
    config = load_config()

    backend = threading.Thread(target=_run_backend_thread, args=(config,), daemon=True)
    backend.start()

    webview.create_window(
        "Numpty Flag",
        url=overlay_html_uri(),
        transparent=True,
        frameless=True,
        easy_drag=True,
        on_top=True,
        width=440,
        height=380,
    )
    webview.start()


if __name__ == "__main__":
    main()
