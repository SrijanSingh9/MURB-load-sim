# MURB Load Simulator API

A tiny FastAPI service that simulates a live electricity meter in an apartment building. It returns the building's current electrical load, the panel's safety limit, and how much spare power is available for EV charging right now.

Useful for building and testing EV-charging logic without touching a real electrical panel.

---

## What it returns

Each reading contains five fields:

| Field | Meaning |
|---|---|
| `time` | Current timestamp |
| `current_load_kw` | Building's current power draw (kW) |
| `max_panel_capacity_kw` | Panel's absolute safety limit (kW) |
| `safety_buffer_kw` | Reserved safety margin (kW) |
| `ev_headroom_kw` | Power an EV charger can safely use right now (kW) |

---

## Why the safety buffer

`ev_headroom_kw = panel − buffer − current_load`

The buffer exists because real buildings aren't still: appliances spike suddenly (fridge, HVAC inrush), meters have ±1–2% error, and NEC 625.41 requires EV chargers to be sized at 125% of rated power. Running a transformer at 100% load also shortens its life.

The API reserves **10 kW** by default so the EV scheduler never plans into that fluctuation zone.

> Set `SAFETY_BUFFER_KW = 0.0` in `main.py` for a toy simulation. Never deploy with 0 in a real building.

---

## Run it

```bash
pip install fastapi uvicorn
python main.py
```

Then open **http://127.0.0.1:8000/docs** for the interactive test UI.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Welcome message and current settings |
| GET | `/reading` | One fresh reading (also saved to history) |
| GET | `/history?limit=20` | Last N readings |

### Example response from `/reading`

```json
{
  "time": "2026-11-17T19:03:30",
  "current_load_kw": 185.3,
  "max_panel_capacity_kw": 250.0,
  "safety_buffer_kw": 10.0,
  "ev_headroom_kw": 54.7
}
```

*"The building is using 185.3 kW. Panel max is 250 kW. After holding back 10 kW for safety, an EV charger can safely pull up to 54.7 kW right now."*

---

## Use it from code

```python
import requests

r = requests.get("http://127.0.0.1:8000/reading").json()

if r["ev_headroom_kw"] >= 7.2:
    print("Safe to start a Level-2 charger")
else:
    print("Not enough room right now")
```

Poll on a schedule:

```python
import time, requests

while True:
    r = requests.get("http://127.0.0.1:8000/reading").json()
    print(f"{r['time']}  load={r['current_load_kw']} kW  ev_can_use={r['ev_headroom_kw']} kW")
    time.sleep(300)   # every 5 minutes
```

---

## Configuration

All at the top of `main.py`:

| Constant | Default | Purpose |
|---|---|---|
| `PANEL_CAPACITY_KW` | `250.0` | Panel rating |
| `SAFETY_BUFFER_KW` | `10.0` | Reserved margin |
| `HISTORY_SIZE` | `100` | How many past readings to keep |

---

## How the load is simulated

A realistic daily curve: low at night, morning bump (~8 AM), evening peak (~7 PM), slightly flatter on weekends, plus occasional random appliance spikes. Good enough to look like a real building when graphed.

---

## Scope

This is a simulator, not a controller. It does **not** talk to a real meter, does **not** command an EV charger, and does **not** replace an electrical engineering review. It exists so you can build the scheduler first and swap in real data later.