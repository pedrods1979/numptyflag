from dataclasses import dataclass, field
from typing import Optional

from .ringbuffer import RingBuffer

INCIDENT_HISTORY_SECONDS = 600  # 10 minutes
GAP_HISTORY_SECONDS = 60


@dataclass
class DriverState:
    car_idx: int
    name: str = ""
    lic_letter: str = ""
    sr: float = 0.0
    irating: int = 0
    car_class_id: int = 0

    incidents_total: int = 0
    laps_completed: int = 0

    gap_seconds: Optional[float] = None
    position: int = 0
    on_pit_road: bool = False
    lap_dist_pct: float = -1.0

    last_alert_time: Optional[float] = None

    incidents_history: RingBuffer = field(
        default_factory=lambda: RingBuffer(INCIDENT_HISTORY_SECONDS)
    )
    gap_history: RingBuffer = field(
        default_factory=lambda: RingBuffer(GAP_HISTORY_SECONDS)
    )
