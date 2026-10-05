from __future__ import annotations
import os, sqlite3, random, math, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "fridge_data.sqlite3"
app = FastAPI(title="Fridge IoT Monitor", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

class Reading(BaseModel):
    device_id: str = Field(default="fridge-01", max_length=80)
    recorded_at: Optional[str] = None
    inside_temp: float = Field(ge=-30, le=60)
    room_temp: float = Field(ge=-20, le=60)
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    current_a: Optional[float] = Field(default=None, ge=0, le=100)
    power_w: Optional[float] = Field(default=None, ge=0, le=10000)
    door_open: Optional[bool] = None

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL,
            recorded_at TEXT NOT NULL, inside_temp REAL NOT NULL, room_temp REAL NOT NULL,
            humidity REAL, current_a REAL, power_w REAL, door_open INTEGER)""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(recorded_at)")

@app.on_event("startup")
def startup():
    init_db()

def insert_reading(r: Reading):
    stamp = r.recorded_at or datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute("""INSERT INTO readings(device_id,recorded_at,inside_temp,room_temp,humidity,current_a,power_w,door_open)
        VALUES(?,?,?,?,?,?,?,?)""", (r.device_id, stamp, r.inside_temp, r.room_temp, r.humidity,
        r.current_a, r.power_w, None if r.door_open is None else int(r.door_open)))
    return stamp

def get_rows(limit=240):
    with db() as con:
        return con.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()[::-1]

def evaluate(rows):
    if not rows:
        return {"level":"unknown","message":"データ待機中","notify_after_min":None,"rise_rate":None}
    latest = rows[-1]
    # Approximate recent slope from up to 10 minutes of readings (or available range).
    recent = [r for r in rows if r["device_id"] == latest["device_id"]][-20:]
    rise = None
    if len(recent) >= 2:
        try:
            t0 = datetime.fromisoformat(recent[0]["recorded_at"].replace("Z","+00:00")).timestamp()
            t1 = datetime.fromisoformat(recent[-1]["recorded_at"].replace("Z","+00:00")).timestamp()
            dt = (t1-t0)/60
            if dt > 0: rise = (recent[-1]["inside_temp"]-recent[0]["inside_temp"])/dt
        except Exception:
            pass
    room = latest["room_temp"]; inside = latest["inside_temp"]
    # These are configurable prototype heuristics, not food-safety thresholds.
    if inside >= 8 or (rise is not None and rise >= 0.35 and room >= 30):
        level, msg, mins = "danger", "庫内温度または上昇傾向に注意。食品の状態を確認してください。", 0
    elif (inside >= 5) or (rise is not None and rise >= 0.2) or (latest["door_open"] == 1):
        level, msg, mins = "warning", "温度上昇または扉の開放を検知しています。", 5 if room >= 30 else 10 if room >= 22 else 15
    else:
        level, msg, mins = "normal", "現在の計測値に大きな注意条件はありません。", None
    return {"level":level,"message":msg,"notify_after_min":mins,"rise_rate":None if rise is None else round(rise,3)}

@app.get("/")
def home():
    return FileResponse(BASE/"static"/"index.html")

@app.post("/api/reading")
def post_reading(r: Reading):
    stamp = insert_reading(r)
    return {"ok":True,"recorded_at":stamp}

@app.get("/api/history")
def history(limit: int=120):
    limit = max(1,min(limit,1000))
    rows=get_rows(limit)
    return [dict(r) for r in rows]

@app.get("/api/status")
def status():
    rows=get_rows(240)
    if not rows:
        return {"latest":None,"alert":evaluate(rows)}
    latest=dict(rows[-1])
    latest["door_open"] = None if latest["door_open"] is None else bool(latest["door_open"])
    return {"latest":latest,"alert":evaluate(rows)}

@app.post("/api/demo")
def demo():
    # Adds a plausible demonstration point; no physical sensors are read.
    rows=get_rows(1)
    if rows:
        prev=rows[-1]
        inside=float(prev["inside_temp"]); room=float(prev["room_temp"])
    else:
        inside,room=4.0,24.0
    # Smooth random walk with occasional simulated door-open warming.
    door = random.random() < 0.08
    room=max(10,min(38,room+random.uniform(-0.5,0.5)))
    inside += (room-inside)*(0.10 if door else 0.008)+random.uniform(-0.12,0.12)
    inside=max(-2,min(16,inside))
    current=0.35 if random.random()<0.6 else 0.03
    power=round(current*100*random.uniform(0.8,1.1),1)
    r=Reading(inside_temp=round(inside,2),room_temp=round(room,2),humidity=round(random.uniform(35,65),1),
              current_a=current,power_w=power,door_open=door)
    insert_reading(r)
    return {"ok":True}

@app.delete("/api/history")
def clear_history():
    with db() as con: con.execute("DELETE FROM readings")
    return {"ok":True}
