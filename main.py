# ================================================================
# SIMPLE MURB LOAD SIMULATOR
# ----------------------------------------------------------------
# Pretends to be a live electricity meter in an apartment building.
# Every time you call it, it returns three numbers:
#     time              - what time it is
#     current_load_kw   - how much power the building is using now
#     max_panel_capacity_kw - the building's hard safety limit
#
# It also returns two bonus numbers:
#     safety_buffer_kw  - reserved margin (see explanation below)
#     ev_headroom_kw    - how much power an EV charger can safely use NOW
#
# How to RUN:
#     pip install fastapi uvicorn
#     python main.py
#
# How to USE:
#     Open   http://127.0.0.1:8000/docs    in your browser
#     (FastAPI gives you a clickable test page for free)
#
#     Or use curl / a script:
#         curl http://127.0.0.1:8000/reading
#         curl http://127.0.0.1:8000/history
# ================================================================


# ---- Imports ---------------------------------------------------
import random
from datetime import datetime
from fastapi import FastAPI


# ---- SETTINGS (change these if you want) -----------------------

# The absolute maximum the building's electrical panel can carry.
PANEL_CAPACITY_KW = 250.0

# Safety buffer in kW.
# WHY: real buildings have sudden load spikes (fridges, motors,
# HVAC startup). If we planned EV charging right up to the panel
# limit, one spike would trip the main breaker.
# Holding back 10 kW creates a small "don't cross" zone.
# Set to 0.0 to see what raw numbers look like — but do NOT
# deploy with 0 in a real building.
SAFETY_BUFFER_KW = 10.0

# How many past readings to remember (so /history can return them).
HISTORY_SIZE = 100


# ---- MEMORY (just a plain list, nothing fancy) -----------------
all_readings = []


# ---- THE SIMULATOR ---------------------------------------------

def make_one_reading():
    """
    Fake ONE reading from the building and return it as a dict.
    """

    # --- Step 1: what time is it? ------------------------------
    now = datetime.now()

    # --- Step 2: how busy is the building right now? ----------
    # In real life, an apartment building is busiest in the
    # morning (7-9am) and the evening (6-9pm). We imitate that
    # with two simple "bumps" added together.
    hour = now.hour + now.minute / 60.0

    busy = 0.2                                # quiet baseline at night
    busy += 0.5 * max(0.0, 1.0 - abs(hour - 8)  / 2.0)   # morning bump
    busy += 0.8 * max(0.0, 1.0 - abs(hour - 19) / 2.5)   # evening bump
    busy = min(busy, 1.0)                     # never above 100%

    # --- Step 3: convert "busy" into actual kW -----------------
    # At full busy we assume the apartments use 85% of the panel.
    load_kw = busy * PANEL_CAPACITY_KW * 0.85

    # Add a little jitter so it doesn't look robotic (±5 kW).
    load_kw += random.uniform(-5.0, 5.0)

    # Occasionally a real appliance turns on (5% of the time).
    if random.random() < 0.05:
        load_kw += random.uniform(10.0, 25.0)

    # Never below 0, never above the panel's hard limit.
    load_kw = max(0.0, min(load_kw, PANEL_CAPACITY_KW))

    # --- Step 4: how much can an EV charger use RIGHT NOW? ----
    # Only the space left after (panel - buffer - building load).
    ev_headroom = PANEL_CAPACITY_KW - SAFETY_BUFFER_KW - load_kw
    ev_headroom = max(0.0, ev_headroom)       # never negative

    # --- Step 5: return the reading as a dict ------------------
    return {
        "time": now.isoformat(timespec="seconds"),
        "current_load_kw":        round(load_kw, 1),
        "max_panel_capacity_kw":  PANEL_CAPACITY_KW,
        "safety_buffer_kw":       SAFETY_BUFFER_KW,
        "ev_headroom_kw":         round(ev_headroom, 1),
    }


# ---- THE API (FastAPI turns functions into URLs) ---------------

app = FastAPI(title="Simple MURB Simulator")


@app.get("/")
def home():
    """Hello !."""
    return {
        "message": "I am a electricity meter simulator for an apartment building.",
        "try_these": {
            "/reading": "Get ONE live reading right now",
            "/history": "Get the last N readings (default 20)",
            "/docs":    "Open this in a browser to click and test",
        },
        "settings": {
            "panel_capacity_kw": PANEL_CAPACITY_KW,
            "safety_buffer_kw":  SAFETY_BUFFER_KW,
        },
    }


@app.get("/reading")
def get_reading():
    """
    Return ONE fresh reading.
    We also save it so /history can show it later.
    """
    r = make_one_reading()
    all_readings.append(r)

    # Keep the list from growing forever
    if len(all_readings) > HISTORY_SIZE:
        all_readings.pop(0)

    return r


@app.get("/history")
def get_history(limit: int = 20):
    """
    Return the last `limit` readings.
    If you haven't called /reading yet, this fills the list
    automatically so you always get something back.
    """
    while len(all_readings) < limit:
        all_readings.append(make_one_reading())

    return all_readings[-limit:]


# ---- START THE SERVER ------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)