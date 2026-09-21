"""SQLite persistence layer for Command Center analytics."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH=Path("data/command_center.db")
SCHEMA="""CREATE TABLE IF NOT EXISTS snapshots(
id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL UNIQUE,epoch INTEGER NOT NULL,
translation_percent REAL NOT NULL,review_percent REAL NOT NULL,files INTEGER NOT NULL,
strings INTEGER NOT NULL,translated INTEGER NOT NULL,reviewed INTEGER NOT NULL,words INTEGER NOT NULL,
delta_translated INTEGER NOT NULL,delta_reviewed INTEGER NOT NULL,payload_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_snapshots_epoch ON snapshots(epoch);"""

def connect(path:Path=DB_PATH)->sqlite3.Connection:
    path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path);db.row_factory=sqlite3.Row;db.executescript(SCHEMA);return db

def record_snapshot(payload:dict[str,Any],path:Path=DB_PATH)->None:
    s,p=payload["stats"],payload["progress"]
    with connect(path) as db:
        db.execute("""INSERT INTO snapshots(timestamp,epoch,translation_percent,review_percent,files,strings,translated,reviewed,words,delta_translated,delta_reviewed,payload_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(timestamp) DO UPDATE SET payload_json=excluded.payload_json""",
        (payload["timestamp"],payload["history"]["latest_epoch"],s["translation_percent"],s["review_percent"],s["files"],s["strings"],s["translated"],s["reviewed"],s["words"],p["delta_translated"],p["delta_reviewed"],json.dumps(payload,ensure_ascii=False,sort_keys=True)))

def recent(limit:int=30,path:Path=DB_PATH)->list[dict[str,Any]]:
    with connect(path) as db:
        rows=db.execute("SELECT payload_json FROM snapshots ORDER BY epoch DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall()
    return [json.loads(r["payload_json"]) for r in reversed(rows)]
