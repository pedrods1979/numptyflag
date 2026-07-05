# Numpty Flag

A lightweight overlay that watches the cars immediately around you in an
iRacing session and flags drivers who are having a messy race, so you can
give a numpty ahead more margin into braking zones, or stop defending
against a fast-but-wild car that's about to have you off.

Two alerts:

- **Numpty ahead** — persistent red highlight on the strip for a car ahead
  that's racking up incidents. No toast spam; you're looking at the strip
  into every braking zone anyway.
- **Let him go** — a toast when a scrappy/numpty car behind is within 1.5s
  and closing fast. Not worth defending against.

See the design notes for the full data model, scoring formula and state
machine — this README only covers running the thing.

## Install

```
pip install -r requirements.txt
```

`pyirsdk` only works on Windows (it talks to iRacing's shared memory), so the
collector and live pipeline need to run on the same Windows machine as the
sim. The threat engine, tests, and record/replay tooling are plain Python and
run anywhere.

## Run against a live iRacing session

iRacing must be in **borderless windowed** mode so the overlay can sit on
top of it.

```
# Terminal 1: collector + threat engine + websocket server
python -m numpty_flag.main

# Terminal 2: frameless transparent overlay window
python -m numpty_flag.overlay_window
```

Or skip the pywebview window entirely and add `overlay/index.html` as an OBS
browser source if you're streaming.

## Develop / tune without iRacing running

Record a few minutes of a real session once, then replay it as many times
as you like while you tune `config.json` or the overlay:

```
python tools/record_session.py recordings/race1.pkl --seconds 300
python tools/replay.py recordings/race1.pkl --realtime
```

`replay.py` runs the same threat engine and websocket server as `main.py`,
so `overlay_window.py` (or an OBS source) works unmodified against it.

## Tests

```
pytest
```

Covers the ring buffer, session-change resets, recent-incident weighting,
gap wrap-around handling, score/state thresholds, and the "let him go"
alert + cooldown logic.

## Tuning

All thresholds live in `config.json` (proximity window, score weights, SR
modifiers, state cutoffs, let-him-go conditions, poll/broadcast rates). The
shipped defaults are a starting point for Porsche Cup fixed; endurance /
multiclass racing will want different numbers — nothing needs a code change,
just edit the JSON.

## Layout

```
numpty_flag/
  collector.py       iRacing SDK wrapper (pyirsdk)
  state.py           per-driver state + ring buffers
  threat_engine.py   scoring, states, "let him go" alerts, session reset
  server.py          websocket broadcaster
  main.py            wires collector -> engine -> server
  overlay_window.py  frameless transparent pywebview window
overlay/
  index.html / style.css / overlay.js   the strip + toast UI
tools/
  record_session.py  record live SDK frames to a pickle
  replay.py          replay a recording through the engine + server
tests/
```

## Known limitations

- No fault attribution — a contact pings both cars involved. The flag means
  "risk near this car", not "this driver caused it".
- Session info updates lag live telemetry by a few seconds (iRacing SDK
  behaviour, not something this project can fix).
- Off-track detection for cars at distance is approximate.
