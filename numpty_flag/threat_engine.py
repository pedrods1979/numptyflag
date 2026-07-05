import math
import re
from typing import Dict, List, Optional

from .state import DriverState

LIC_RE = re.compile(r"^([A-R])\s*([\d.]+)?")


def parse_license(lic_string: str):
    if not lic_string:
        return "", 0.0
    m = LIC_RE.match(lic_string.strip())
    if not m:
        return lic_string.strip(), 0.0
    letter = m.group(1)
    sr = float(m.group(2)) if m.group(2) else 0.0
    return letter, sr


class ThreatEngine:
    """Tracks per-driver incident/gap history and derives threat scores.

    Consumes two update streams: slow session-info (YAML) updates carrying
    incident counts, and fast telemetry updates carrying track position.
    """

    def __init__(self, config: dict):
        self.config = config
        self.drivers: Dict[int, DriverState] = {}
        self.player_car_idx: Optional[int] = None
        self.session_num: Optional[int] = None
        self.team_racing: bool = False
        self.driver_car_est_lap_time: float = 0.0
        self.session_time: float = 0.0
        self.alerts: List[dict] = []

    # ------------------------------------------------------------------
    # Session info (slow YAML updates, every ~2-5s)
    # ------------------------------------------------------------------
    def on_session_info(self, info: dict) -> None:
        session_num = info.get("session_num")
        if self.session_num is not None and session_num != self.session_num:
            self._reset()
        self.session_num = session_num

        self.player_car_idx = info.get("driver_car_idx")
        self.team_racing = info.get("team_racing", False)
        est_lap_time = info.get("driver_car_est_lap_time") or 0.0
        if est_lap_time > 0:
            self.driver_car_est_lap_time = est_lap_time

        incident_field = "TeamIncidentCount" if self.team_racing else "CurDriverIncidentCount"

        for driver in info.get("drivers", []):
            car_idx = driver.get("CarIdx")
            if car_idx is None or car_idx < 0:
                continue
            state = self.drivers.setdefault(car_idx, DriverState(car_idx=car_idx))
            state.name = driver.get("UserName", state.name)
            state.lic_letter, state.sr = parse_license(driver.get("LicString", ""))
            state.irating = driver.get("IRating", state.irating)
            state.car_class_id = driver.get("CarClassID", state.car_class_id)

            incidents = driver.get(incident_field)
            if incidents is None:
                continue
            state.incidents_total = incidents
            state.incidents_history.append(self.session_time, state.incidents_total)

    def _reset(self) -> None:
        self.drivers.clear()
        self.alerts = []

    # ------------------------------------------------------------------
    # Telemetry (fast updates, polled at ~10 Hz)
    # ------------------------------------------------------------------
    def on_telemetry(self, telem: dict) -> None:
        self.session_time = telem.get("session_time", self.session_time)
        laps = telem.get("laps", [])
        est_time = telem.get("est_time", [])
        lap_dist_pct = telem.get("lap_dist_pct", [])
        on_pit_road = telem.get("on_pit_road", [])
        position = telem.get("position", [])

        if self.player_car_idx is None or self.player_car_idx >= len(est_time):
            return

        my_lap = laps[self.player_car_idx] if self.player_car_idx < len(laps) else 0
        my_est_time = est_time[self.player_car_idx]
        lap_time = self.driver_car_est_lap_time

        for car_idx, state in self.drivers.items():
            if car_idx >= len(est_time):
                continue
            state.lap_dist_pct = lap_dist_pct[car_idx] if car_idx < len(lap_dist_pct) else -1.0
            state.on_pit_road = bool(on_pit_road[car_idx]) if car_idx < len(on_pit_road) else False
            state.laps_completed = laps[car_idx] if car_idx < len(laps) else state.laps_completed
            state.position = position[car_idx] if car_idx < len(position) else state.position

            if car_idx == self.player_car_idx:
                state.gap_seconds = 0.0
                continue
            if state.lap_dist_pct < 0:
                state.gap_seconds = None
                continue

            other_est_time = est_time[car_idx]
            other_lap = laps[car_idx] if car_idx < len(laps) else my_lap
            raw_delta = other_est_time - my_est_time
            # EstTime resets every lap; a same-lap delta over half a lap means
            # we've actually wrapped around the start/finish line.
            if lap_time > 0 and abs(raw_delta) > lap_time / 2:
                raw_delta -= math.copysign(lap_time, raw_delta)
            gap = raw_delta + (other_lap - my_lap) * lap_time
            state.gap_seconds = gap
            state.gap_history.append(self.session_time, gap)

        self._evaluate_alerts()

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------
    def _recent_incidents(self, state: DriverState, window_laps: float) -> float:
        lap_time = self.driver_car_est_lap_time
        window_seconds = window_laps * lap_time if lap_time > 0 else 0
        baseline = state.incidents_history.value_at_or_before(
            self.session_time - window_seconds, default=0
        )
        return max(state.incidents_total - baseline, 0)

    def _closing_rate(self, state: DriverState) -> float:
        """Seconds-per-lap the gap is closing, positive = closing on the player."""
        history = state.gap_history
        if len(history) < 2:
            return 0.0
        oldest = history.oldest()
        newest = history.newest()
        window = newest[0] - oldest[0]
        if window <= 0:
            return 0.0
        closing_per_second = (newest[1] - oldest[1]) / window
        lap_time = self.driver_car_est_lap_time
        return closing_per_second * lap_time if lap_time > 0 else closing_per_second

    def score(self, state: DriverState):
        cfg = self.config
        rate = state.incidents_total / max(state.laps_completed, 1)
        recent = self._recent_incidents(state, cfg["recent_window_laps"])

        sr_modifier = 0.0
        if state.lic_letter in cfg["sr_good_letters"] and state.sr >= cfg["sr_good_min"]:
            sr_modifier = cfg["sr_good_modifier"]
        elif state.lic_letter in cfg["sr_bad_letters"] or state.sr < cfg["sr_bad_max"]:
            sr_modifier = cfg["sr_bad_modifier"]

        total_score = cfg["weight_recent"] * recent + cfg["weight_rate"] * rate + sr_modifier
        recent_2 = self._recent_incidents(state, cfg["numpty_recent_window_laps"])

        is_numpty = (
            total_score >= cfg["numpty_score_min"]
            or recent_2 >= cfg["numpty_recent_threshold"]
            or state.incidents_total >= cfg["numpty_total_threshold"]
        )
        if is_numpty:
            level = "NUMPTY"
        elif total_score >= cfg["clean_score_max"]:
            level = "SCRAPPY"
        else:
            level = "CLEAN"
        return total_score, level, recent

    def _in_proximity(self, state: DriverState) -> bool:
        if state.gap_seconds is None:
            return False
        if state.on_pit_road or state.lap_dist_pct < 0:
            return False
        return abs(state.gap_seconds) <= self.config["proximity_seconds"]

    def _evaluate_alerts(self) -> None:
        cfg = self.config
        self.alerts = []
        for car_idx, state in self.drivers.items():
            if car_idx == self.player_car_idx or not self._in_proximity(state):
                continue
            if state.gap_seconds >= 0:
                continue  # "let him go" only applies to cars behind

            _, level, _ = self.score(state)
            closing = self._closing_rate(state)
            if (
                level in ("SCRAPPY", "NUMPTY")
                and abs(state.gap_seconds) <= cfg["let_him_go_gap_seconds"]
                and closing >= cfg["let_him_go_closing_threshold"]
            ):
                last = state.last_alert_time
                if last is None or self.session_time - last >= cfg["let_him_go_cooldown_seconds"]:
                    state.last_alert_time = self.session_time
                    self.alerts.append(
                        {
                            "car_idx": car_idx,
                            "message": (
                                f"P{state.position} {state.name} — {state.incidents_total}x, "
                                f"closing {closing:.1f}/lap — give room"
                            ),
                        }
                    )

    def build_payload(self) -> dict:
        cars = []
        player = None
        for car_idx, state in self.drivers.items():
            if car_idx == self.player_car_idx:
                player = {
                    "car_idx": car_idx,
                    "name": state.name,
                    "pos": state.position,
                    "lic": f"{state.lic_letter} {state.sr:.2f}".strip(),
                    "inc": state.incidents_total,
                }
                continue
            in_range = self._in_proximity(state)
            total_score, level, recent = self.score(state)
            cars.append(
                {
                    "car_idx": car_idx,
                    "name": state.name,
                    "pos": state.position,
                    "lic": f"{state.lic_letter} {state.sr:.2f}".strip(),
                    "inc": state.incidents_total,
                    "recent": recent,
                    "gap": round(state.gap_seconds, 2) if state.gap_seconds is not None else None,
                    "closing": round(self._closing_rate(state), 2),
                    "score": round(total_score, 2),
                    "state": level if in_range else "CLEAN",
                    "in_range": in_range,
                }
            )
        cars.sort(key=lambda c: (c["gap"] is None, c["gap"]))
        return {
            "player_car_idx": self.player_car_idx,
            "player": player,
            "session_num": self.session_num,
            "session_time": self.session_time,
            "cars": cars,
            "alerts": self.alerts,
        }
