"""Replay a recording made by record_session.py through the threat engine
and websocket server, so the overlay can be exercised without iRacing running.
"""

import argparse
import asyncio
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from numpty_flag.config import load_config  # noqa: E402
from numpty_flag.server import OverlayServer  # noqa: E402
from numpty_flag.threat_engine import ThreatEngine  # noqa: E402


async def replay(frames, engine: ThreatEngine, realtime: bool) -> None:
    prev_wall = None
    for frame in frames:
        engine.on_session_info(frame["session_info"])
        engine.on_telemetry(frame["telemetry"])
        if realtime and prev_wall is not None:
            await asyncio.sleep(max(frame["wall_time"] - prev_wall, 0))
        prev_wall = frame["wall_time"]
    print("Replay finished; server keeps broadcasting the final snapshot.")
    while True:
        await asyncio.sleep(3600)


async def main_async(path: str, realtime: bool) -> None:
    with open(path, "rb") as f:
        frames = pickle.load(f)

    config = load_config()
    engine = ThreatEngine(config)
    server = OverlayServer(
        engine,
        host=config["websocket_host"],
        port=config["websocket_port"],
        hz=config["broadcast_hz"],
    )

    await asyncio.gather(
        replay(frames, engine, realtime),
        server.run(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to a pickle file created by record_session.py")
    parser.add_argument("--realtime", action="store_true", help="Pace playback to match the original recording")
    args = parser.parse_args()
    asyncio.run(main_async(args.path, args.realtime))
