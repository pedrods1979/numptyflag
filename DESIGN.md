# Numpty Flag — iRacing Live Incident Threat Overlay

## Purpose

A lightweight overlay that watches the cars immediately around the player and flags,
in real time, drivers who are having a messy race — so the player can decide to keep
distance, defend less aggressively, or let a fast-but-wild car through.

Two core alerts:

1. **"Numpty ahead"** — the car in front is racking up incidents; give margin into braking zones.
2. **"Let him go"** — the car behind is both incident-prone *and* closing quickly; not worth defending.

---

## 1. Data sources (iRacing SDK via pyirsdk or irsdk-node)

### Session info YAML (updates every ~2–5 s)

| Field | Use |
|---|---|
| `DriverInfo.DriverCarIdx` | Player's own CarIdx |
| `DriverInfo.Drivers[].CarIdx` | Key for all per-car arrays |
| `DriverInfo.Drivers[].UserName` | Display name |
| `DriverInfo.Drivers[].CurDriverIncidentCount` | **Primary signal** — live incident count this session |
| `DriverInfo.Drivers[].TeamIncidentCount` | Use instead of CurDriver in team events |
| `DriverInfo.Drivers[].LicString` (e.g. `"A 3.42"`) | SR baseline modifier |
| `DriverInfo.Drivers[].IRating` | Display only |
| `DriverInfo.Drivers[].CarClassID` | Multiclass handling |
| `SessionNum` / `SessionInfo` | Detect session change (practice → quali → race) |

### Live telemetry (60 Hz; poll at 10 Hz, that's plenty)

| Field | Use |
|---|---|
| `CarIdxLapDistPct[]` | Track position 0.0–1.0 (−1 = not on world) |
| `CarIdxLap[]` | Laps completed per car (denominator for incident rate) |
| `CarIdxEstTime[]` | Estimated time around lap — used for gaps in seconds |
| `CarIdxOnPitRoad[]` | Exclude cars in pits from alerts |
| `CarIdxPosition[]` / `CarIdxClassPosition[]` | Display |
| `SessionTime` | Timestamps for ring buffers |

---

## 2. Per-driver state (dict keyed by CarIdx)

```
{
  car_idx, name, lic_letter, sr, irating, car_class,
  incidents_total,          # latest CurDriverIncidentCount
  incidents_history,        # ring buffer of (session_time, count), keep ~10 min
  laps_completed,
  gap_seconds,              # signed: + ahead of player, − behind
  gap_history,              # ring buffer of (session_time, gap), keep ~60 s
}
```

Rebuild/reset all state when `SessionNum` changes — incident counts reset between
practice, quali and race.

---

## 3. Derived metrics

**Incident rate**

`rate = incidents_total / max(laps_completed, 1)`

Normalises early-race chaos vs late-race totals. 1x/lap sustained is genuinely bad.

**Recent incidents (the "hot right now" signal)**

`recent = incidents_total − count_at(session_time − 3 laps' worth of time)`

from the ring buffer. A driver who picked up 6x in the last 3 laps is more dangerous
than one carrying 8x from a lap-1 pileup and clean since. Weight this highest.

**SR modifier** (small nudge only — session behaviour beats reputation)

- Licence A/B with SR ≥ 3.0 → −0.5 to score
- Licence D/R or SR < 2.0 → +0.5 to score

**Closing rate (cars behind only)**

`closing = (gap_history oldest − gap_history newest) / window_seconds`

expressed as seconds-per-lap gained on the player, using ~30–60 s of gap history.

---

## 4. Threat score & states

```
score = (2.0 × recent) + (1.5 × rate) + sr_modifier
```

| State | Condition | Colour |
|---|---|---|
| CLEAN | score < 2 | grey/green |
| SCRAPPY | 2 ≤ score < 5 | amber |
| NUMPTY | score ≥ 5, OR ≥ 4x in last 2 laps, OR ≥ 12x total | red |

**"Let him go" alert (behind only):**
fires when a SCRAPPY or NUMPTY car behind is within 1.5 s AND closing ≥ 0.3 s/lap.
Message: `"P{pos} {name} — {inc}x, closing {rate}/lap — give room"`.
Cooldown 60 s per driver so it doesn't nag.

**"Numpty ahead" indicator:** persistent red highlight on the relative strip, no toast
spam — you'll be looking at the strip into every braking zone anyway.

All thresholds live in a `config.json` so they're tunable without code changes.
Defaults above are a starting point for Porsche Cup fixed; endurance multiclass
will want different numbers.

---

## 5. Scope & filtering

- Only evaluate cars within **±5 s** of the player via `CarIdxEstTime` delta
  (handle lap wrap: if raw delta > half the player's lap time, subtract/add a lap).
- Skip cars where `CarIdxLapDistPct == −1` (towing/exited) or `CarIdxOnPitRoad == true`.
- Multiclass: evaluate everyone in proximity regardless of class — a wild LMP2
  lapping your GT3 is exactly what you want flagged. Show class colour on the strip.
- Team sessions: swap `CurDriverIncidentCount` → `TeamIncidentCount` (detect via
  `WeekendInfo.TeamRacing`).

---

## 6. Known limitations (accept, don't fight)

- **No fault attribution.** A 4x contact pings both cars. The flag means "risk near
  this car", not "this driver is at fault". Recent-weighted scoring softens this —
  an innocent victim stops accruing, a repeat offender doesn't.
- Session info YAML lags a few seconds behind reality. Fine for this use case.
- Off-track (1x) detection for *other* cars can be approximate at distance.

---

## 7. Architecture

```
[iRacing shared memory]
        │  pyirsdk, 10 Hz poll + YAML parse on change
        ▼
[Python collector] ── threat engine (sections 2–4) ── config.json
        │  websocket, JSON snapshot @ 4 Hz
        ▼
[HTML/JS overlay page]
   • transparent background
   • rendered in a frameless always-on-top window (pywebview/Electron)
     OR added as an OBS browser source for streaming
```

Why websocket + HTML rather than a native PyQt canvas: it's the same pattern as
irDashies, trivially OBS-compatible, and the UI iterates fast. iRacing must run in
**borderless windowed** mode for the overlay to sit on top.

**Overlay layout:** relative-style strip, 3 ahead / player / 3 behind:
`[pos] [name] [lic] [inc count + trend ▲] [gap]`, row background = threat colour.
Toast area above the strip for "let him go" alerts.

### JSON payload example

```json
{
  "player_car_idx": 12,
  "cars": [
    {"car_idx": 7, "name": "J Bloggs", "lic": "B 2.41", "inc": 12,
     "recent": 5, "gap": -0.8, "closing": 0.4, "state": "NUMPTY",
     "alert": "let_him_go"}
  ]
}
```

---

## 8. Build order

1. Collector: connect pyirsdk, print incident table for all drivers each YAML update.
2. Add telemetry poll: gaps via `CarIdxEstTime`, proximity filter, lap-wrap handling.
3. Threat engine: ring buffers, score, states, session-change reset.
4. Websocket server + minimal HTML strip.
5. Frameless transparent window (pywebview) / OBS source.
6. Tune thresholds over a week of Porsche Cup races; adjust `config.json`.

Test without iRacing running by recording a few minutes of real session data to
disk (pickle the dicts) and replaying it into the engine.
