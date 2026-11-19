# ================================================================
# SIMPLE MURB LOAD SIMULATOR
# ----------------------------------------------------------------
# Pretends to be a live electricity meter in an apartment building.
#
# RUN:
#     pip install fastapi uvicorn
#     python main.py
#
# USE:
#     Open http://127.0.0.1:8000/docs  (interactive test UI)
# ================================================================

from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import random
from fastapi import FastAPI


# ---- SETTINGS --------------------------------------------------

PANEL_CAPACITY_KW = 250.0
SAFETY_BUFFER_KW = 10.0
HISTORY_SIZE = 100
SAMPLE_INTERVAL_SEC = 30          # how often "the meter" would report


# ---- MEMORY ----------------------------------------------------
# A deque with maxlen automatically drops the oldest reading when full.
# No manual `if len > X: pop(0)` needed.

all_readings: deque = deque(maxlen=HISTORY_SIZE)


# ---- SIMULATOR -------------------------------------------------

def make_one_reading(when: Optional[datetime] = None) -> dict:
    """Produce one fake meter reading at time `when` (defaults to now)."""
    when = when or datetime.now()
    hour = when.hour + when.minute / 60.0

    # Daily "busy" curve: quiet baseline + morning bump + evening peak
    busy = 0.2
    busy += 0.5 * max(0.0, 1.0 - abs(hour - 8) / 2.0)
    busy += 0.8 * max(0.0, 1.0 - abs(hour - 19) / 2.5)
    busy = min(busy, 1.0)

    load_kw = busy * PANEL_CAPACITY_KW * 0.85

    # Small jitter so it doesn't look robotic
    load_kw += random.uniform(-5.0, 5.0)

    # Occasional appliance spike (5% of the time)
    if random.random() < 0.05:
        load_kw += random.uniform(10.0, 25.0)

    load_kw = max(0.0, min(load_kw, PANEL_CAPACITY_KW))

    ev_headroom = max(0.0, PANEL_CAPACITY_KW - SAFETY_BUFFER_KW - load_kw)

    return {
        "time": when.isoformat(timespec="seconds"),
        "current_load_kw": round(load_kw, 1),
        "max_panel_capacity_kw": PANEL_CAPACITY_KW,
        "safety_buffer_kw": SAFETY_BUFFER_KW,
        "ev_headroom_kw": round(ev_headroom, 1),
    }


def seed_history_once(limit: int) -> None:
    """
    If history is empty, fill it with BACKDATED readings spaced
    SAMPLE_INTERVAL_SEC apart. Runs only once — after that, real
    readings from /reading take over.
    """
    if all_readings:
        return

    now = datetime.now()
    for i in range(limit, 0, -1):
        all_readings.append(make_one_reading(now - timedelta(seconds=i * SAMPLE_INTERVAL_SEC)))


# ---- API -------------------------------------------------------

app = FastAPI(title="Simple MURB Simulator")


@app.get("/")
def home() -> dict:
    return {
        "message": "Electricity meter simulator for an apartment building.",
        "try_these": {
            "/reading": "Get ONE live reading right now",
            "/history": "Get the last N readings (default 20)",
            "/docs": "Open in a browser to click and test",
        },
        "settings": {
            "panel_capacity_kw": PANEL_CAPACITY_KW,
            "safety_buffer_kw": SAFETY_BUFFER_KW,
        },
    }


@app.get("/reading")
def get_reading() -> dict:
    """Return one fresh reading and record it in history."""
    r = make_one_reading()
    all_readings.append(r)
    return r


@app.get("/history")
def get_history(limit: int = 20) -> list[dict]:
    """Return the last `limit` readings, oldest first."""
    seed_history_once(limit)
    return list(all_readings)[-limit:]


# ---- ENTRYPOINT ------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)