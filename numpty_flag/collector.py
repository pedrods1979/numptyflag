"""Thin wrapper around pyirsdk exposing only the fields Numpty Flag needs."""

try:
    import irsdk
except ImportError:  # pragma: no cover - exercised only without the SDK installed
    irsdk = None


class IRacingCollector:
    def __init__(self):
        if irsdk is None:
            raise RuntimeError("pyirsdk is not installed; `pip install pyirsdk`")
        self.ir = irsdk.IRSDK()

    def connect(self) -> bool:
        if not self.ir.is_initialized:
            self.ir.startup()
        return bool(self.ir.is_connected)

    def is_connected(self) -> bool:
        return bool(self.ir.is_initialized and self.ir.is_connected)

    def read_session_info(self) -> dict:
        driver_info = self.ir["DriverInfo"] or {}
        weekend_info = self.ir["WeekendInfo"] or {}
        return {
            "session_num": self.ir["SessionNum"],
            "driver_car_idx": driver_info.get("DriverCarIdx"),
            "drivers": driver_info.get("Drivers", []),
            "driver_car_est_lap_time": driver_info.get("DriverCarEstLapTime") or 0.0,
            "team_racing": bool(int(weekend_info.get("TeamRacing", 0) or 0)),
        }

    def read_telemetry(self) -> dict:
        return {
            "session_time": self.ir["SessionTime"] or 0.0,
            "lap_dist_pct": self.ir["CarIdxLapDistPct"] or [],
            "laps": self.ir["CarIdxLap"] or [],
            "est_time": self.ir["CarIdxEstTime"] or [],
            "on_pit_road": self.ir["CarIdxOnPitRoad"] or [],
            "position": self.ir["CarIdxPosition"] or [],
            "class_position": self.ir["CarIdxClassPosition"] or [],
        }
