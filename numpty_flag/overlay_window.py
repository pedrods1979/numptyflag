"""Frameless, transparent, always-on-top window hosting the overlay HTML.

Run alongside `python -m numpty_flag.main` (which serves the websocket feed).
iRacing must be in borderless windowed mode for this to sit on top of it.

For a single-process/single-exe setup, use `numpty_flag.app` instead.
"""

import webview

from .paths import overlay_html_uri


def launch() -> None:
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
    launch()
