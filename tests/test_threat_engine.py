import pytest

from numpty_flag.config import load_config
from numpty_flag.state import DriverState
from numpty_flag.threat_engine import ThreatEngine, parse_license


def make_driver(car_idx, name="Driver", lic="A 4.00", irating=2000, car_class=1, incidents=0):
    return {
        "CarIdx": car_idx,
        "UserName": name,
        "LicString": lic,
        "IRating": irating,
        "CarClassID": car_class,
        "CurDriverIncidentCount": incidents,
    }


def make_session_info(session_num, driver_car_idx, drivers, lap_time=90.0, team_racing=False):
    return {
        "session_num": session_num,
        "driver_car_idx": driver_car_idx,
        "drivers": drivers,
        "driver_car_est_lap_time": lap_time,
        "team_racing": team_racing,
    }


def make_telemetry(session_time, laps, est_time, lap_dist_pct=None, on_pit_road=None, position=None):
    n = len(laps)
    return {
        "session_time": session_time,
        "laps": laps,
        "est_time": est_time,
        "lap_dist_pct": lap_dist_pct or [0.5] * n,
        "on_pit_road": on_pit_road or [False] * n,
        "position": position or list(range(1, n + 1)),
    }


@pytest.fixture
def engine():
    return ThreatEngine(load_config())


def test_parse_license():
    assert parse_license("A 4.20") == ("A", 4.20)
    assert parse_license("R 0.90") == ("R", 0.90)
    assert parse_license("") == ("", 0.0)


def test_session_change_resets_incident_state(engine):
    drivers = [make_driver(0, "Player"), make_driver(1, "Rival", incidents=5)]
    engine.on_session_info(make_session_info(0, 0, drivers))
    assert engine.drivers[1].incidents_total == 5

    # New session (e.g. practice -> race): incidents reset, old history discarded.
    new_drivers = [make_driver(0, "Player"), make_driver(1, "Rival", incidents=0)]
    engine.on_session_info(make_session_info(1, 0, new_drivers))
    assert engine.drivers[1].incidents_total == 0
    assert len(engine.drivers[1].incidents_history) == 1


def test_recent_incidents_ignores_stale_pre_window_activity(engine):
    engine.driver_car_est_lap_time = 90.0
    engine.session_time = 300.0
    state = DriverState(car_idx=1)
    state.incidents_total = 8
    # All 8 incidents happened long before the 3-lap (270s) recent window.
    state.incidents_history.append(0.0, 8)

    recent = engine._recent_incidents(state, engine.config["recent_window_laps"])
    assert recent == 0


def test_recent_incidents_counts_activity_inside_window(engine):
    engine.driver_car_est_lap_time = 90.0
    engine.session_time = 300.0
    state = DriverState(car_idx=1)
    state.incidents_history.append(0.0, 2)
    state.incidents_history.append(250.0, 8)  # inside the last 270s
    state.incidents_total = 8

    recent = engine._recent_incidents(state, engine.config["recent_window_laps"])
    assert recent == 6  # 8 - baseline(2) picked up within the window


def test_score_state_thresholds(engine):
    clean = DriverState(car_idx=1, lic_letter="A", sr=4.0, incidents_total=0, laps_completed=5)
    _, level, _ = engine.score(clean)
    assert level == "CLEAN"

    scrappy = DriverState(car_idx=2, lic_letter="B", sr=3.5, incidents_total=2, laps_completed=10)
    _, level, _ = engine.score(scrappy)
    assert level == "SCRAPPY"

    numpty_by_total = DriverState(car_idx=3, lic_letter="A", sr=4.0, incidents_total=12, laps_completed=20)
    _, level, _ = engine.score(numpty_by_total)
    assert level == "NUMPTY"


def test_gap_wrap_handling_around_start_finish_line(engine):
    engine.player_car_idx = 0
    engine.driver_car_est_lap_time = 90.0
    engine.drivers = {0: DriverState(car_idx=0), 1: DriverState(car_idx=1)}

    # Player is just before the line (89.5s into lap), rival just crossed it (0.5s in).
    telem = make_telemetry(
        session_time=100.0,
        laps=[5, 5],
        est_time=[89.5, 0.5],
        lap_dist_pct=[0.99, 0.01],
    )
    engine.on_telemetry(telem)

    assert engine.drivers[1].gap_seconds == pytest.approx(1.0)


def test_let_him_go_alert_fires_once_then_respects_cooldown(engine):
    drivers = [
        make_driver(0, "Player"),
        make_driver(1, "Numpty Norm", lic="D 1.00", incidents=6),
    ]
    engine.on_session_info(make_session_info(0, 0, drivers, lap_time=90.0))

    # First telemetry sample: rival 1.4s behind.
    engine.on_telemetry(make_telemetry(0.0, laps=[0, 0], est_time=[10.0, 8.6]))
    assert engine.alerts == []  # not enough gap history yet to compute closing rate

    # 30s later, rival has closed to 0.7s behind -> closing well above threshold.
    engine.on_telemetry(make_telemetry(30.0, laps=[0, 0], est_time=[40.0, 39.3]))
    assert len(engine.alerts) == 1
    assert "Numpty Norm" in engine.alerts[0]["message"]

    # Still closing 5s later, but inside the 60s cooldown -> no repeat alert.
    engine.on_telemetry(make_telemetry(35.0, laps=[0, 0], est_time=[45.0, 44.3]))
    assert engine.alerts == []


def test_alert_does_not_fire_for_cars_ahead(engine):
    drivers = [
        make_driver(0, "Player"),
        make_driver(1, "Numpty Norm", lic="D 1.00", incidents=6),
    ]
    engine.on_session_info(make_session_info(0, 0, drivers, lap_time=90.0))

    # Rival is ahead (positive gap), closing rapidly -- should never trigger "let him go".
    engine.on_telemetry(make_telemetry(0.0, laps=[0, 0], est_time=[8.6, 10.0]))
    engine.on_telemetry(make_telemetry(30.0, laps=[0, 0], est_time=[39.3, 40.0]))
    assert engine.alerts == []


def test_build_payload_shape(engine):
    drivers = [make_driver(0, "Player"), make_driver(1, "Rival", incidents=1)]
    engine.on_session_info(make_session_info(0, 0, drivers, lap_time=90.0))
    engine.on_telemetry(make_telemetry(0.0, laps=[0, 0], est_time=[10.0, 9.0]))

    payload = engine.build_payload()
    assert payload["player"]["name"] == "Player"
    assert len(payload["cars"]) == 1
    assert payload["cars"][0]["name"] == "Rival"
