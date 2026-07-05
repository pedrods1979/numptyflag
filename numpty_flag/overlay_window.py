"""Frameless, transparent, always-on-top window hosting the overlay HTML.

Run alongside `python -m numpty_flag.main` (which serves the websocket feed).
iRacing must be in borderless windowed mode for this to sit on top of it.
"""

import pathlib

import webview

OVERLAY_HTML = pathlib.Path(__file__).resolve().parent.parent / "overlay" / "index.html"


def launch() -> None:
    webview.create_window(
        "Numpty Flag",
        url=OVERLAY_HTML.as_uri(),
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
