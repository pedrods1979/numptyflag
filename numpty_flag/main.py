import asyncio
import logging

from .collector import IRacingCollector
from .config import load_config
from .server import OverlayServer
from .threat_engine import ThreatEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def poll_loop(collector: IRacingCollector, engine: ThreatEngine, config: dict) -> None:
    telem_interval = 1.0 / config["poll_hz_telemetry"]
    session_interval = config["session_info_poll_seconds"]
    last_session_poll = 0.0

    while True:
        if not collector.is_connected():
            logger.info("Waiting for iRacing...")
            if not collector.connect():
                await asyncio.sleep(1.0)
                continue

        loop_time = asyncio.get_event_loop().time()
        if loop_time - last_session_poll >= session_interval:
            engine.on_session_info(collector.read_session_info())
            last_session_poll = loop_time

        engine.on_telemetry(collector.read_telemetry())
        await asyncio.sleep(telem_interval)


async def run_backend(config: dict) -> None:
    """Collector + threat engine + websocket server, run until cancelled."""
    collector = IRacingCollector()
    engine = ThreatEngine(config)
    server = OverlayServer(
        engine,
        host=config["websocket_host"],
        port=config["websocket_port"],
        hz=config["broadcast_hz"],
    )

    await asyncio.gather(
        poll_loop(collector, engine, config),
        server.run(),
    )


def main() -> None:
    asyncio.run(run_backend(load_config()))


if __name__ == "__main__":
    main()
