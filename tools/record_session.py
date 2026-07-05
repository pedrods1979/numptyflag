"""Record iRacing SDK frames to a pickle file for offline replay.

Run this while iRacing is live, then feed the recording into replay.py to
develop and tune the threat engine / overlay without needing the sim running.
"""

import argparse
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from numpty_flag.collector import IRacingCollector  # noqa: E402


def record(output_path: str, duration_seconds: float, hz: float) -> None:
    collector = IRacingCollector()
    if not collector.connect():
        raise SystemExit("Could not connect to iRacing. Is it running?")

    interval = 1.0 / hz
    frames = []
    start = time.time()
    print(f"Recording for {duration_seconds:.0f}s at {hz:.0f} Hz...")
    while time.time() - start < duration_seconds:
        frames.append(
            {
                "session_info": collector.read_session_info(),
                "telemetry": collector.read_telemetry(),
                "wall_time": time.time(),
            }
        )
        time.sleep(interval)

    with open(output_path, "wb") as f:
        pickle.dump(frames, f)
    print(f"Recorded {len(frames)} frames to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Path to write the pickle file")
    parser.add_argument("--seconds", type=float, default=180.0)
    parser.add_argument("--hz", type=float, default=10.0)
    args = parser.parse_args()
    record(args.output, args.seconds, args.hz)
