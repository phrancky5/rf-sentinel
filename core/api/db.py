"""SQLite persistence for scan history."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import zlib
from pathlib import Path

logger = logging.getLogger("rfsentinel.db")

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "rfsentinel.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS scans (
    id            TEXT PRIMARY KEY,
    start_mhz     REAL NOT NULL,
    stop_mhz      REAL NOT NULL,
    duration      REAL NOT NULL,
    gain          REAL NOT NULL,
    created_at    TEXT NOT NULL,
    duration_s    REAL,
    preset_band   TEXT,
    note          TEXT DEFAULT '',
    spectrum_data BLOB,
    waterfall_data BLOB
);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_frequencies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    freq_mhz    REAL NOT NULL,
    description TEXT NOT NULL,
    scan_id     TEXT,
    preset_band TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_saved_frequencies_created_at ON saved_frequencies(created_at DESC);
"""


def _ensure_column(table: str, column: str, definition: str) -> None:
    if not _conn:
        return
    cols = {row["name"] for row in _conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        _conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init(db_path: Path | None = None) -> None:
    global _conn
    path = db_path or DB_PATH
    os.makedirs(path.parent, exist_ok=True)
    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA foreign_keys=ON")
    _conn.executescript(_SCHEMA)
    _ensure_column("scans", "preset_band", "TEXT")
    _ensure_column("scans", "note", "TEXT DEFAULT ''")
    _conn.commit()
    logger.info("Database ready: %s", path)


def _compress(data: dict) -> bytes:
    return zlib.compress(json.dumps(data, separators=(",", ":")).encode(), level=6)


def _decompress(blob: bytes) -> dict:
    return json.loads(zlib.decompress(blob))


def save_scan(job) -> None:
    if not _conn:
        return
    p = job.params

    spectrum_blob = _compress(p["spectrum_data"]) if "spectrum_data" in p else None
    waterfall_blob = _compress(p["waterfall_data"]) if "waterfall_data" in p else None

    with _lock:
        _conn.execute(
            """INSERT OR REPLACE INTO scans
                    (id, start_mhz, stop_mhz, duration, gain,
                     created_at, duration_s, preset_band, note,
                     spectrum_data, waterfall_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job.id, p["start_mhz"], p["stop_mhz"],
             p["duration"], p["gain"],
                 job.created_at.isoformat(), job.duration_s,
                 p.get("preset_band"), p.get("note", ""),
             spectrum_blob, waterfall_blob),
        )
        _conn.commit()
    logger.info("Saved scan %s", job.id[:8])


def list_scans(limit: int = 50, offset: int = 0) -> dict:
    if not _conn:
        return {"scans": [], "total": 0}
    total = _conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    rows = _conn.execute(
        """SELECT s.id, s.start_mhz, s.stop_mhz, s.duration, s.gain,
                  s.created_at, s.duration_s, s.preset_band, s.note
           FROM scans s ORDER BY s.created_at DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    return {"scans": [dict(r) for r in rows], "total": total}


def delete_scan(scan_id: str) -> bool:
    if not _conn:
        return False
    with _lock:
        cur = _conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        _conn.commit()
    deleted = cur.rowcount > 0
    if deleted:
        logger.info("Deleted scan %s", scan_id[:8])
    return deleted


def get_scan(scan_id: str) -> dict | None:
    if not _conn:
        return None
    row = _conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        return None
    row = dict(row)

    spectrum = _decompress(row.pop("spectrum_data")) if row.get("spectrum_data") else None
    waterfall = _decompress(row.pop("waterfall_data")) if row.get("waterfall_data") else None

    return {
        "id": row["id"],
        "type": "scan",
        "status": "complete",
        "params": {
            "start_mhz": row["start_mhz"],
            "stop_mhz": row["stop_mhz"],
            "duration": row["duration"],
            "gain": row["gain"],
            "preset_band": row.get("preset_band"),
            "note": row.get("note") or "",
            **({"spectrum_data": spectrum} if spectrum else {}),
            **({"waterfall_data": waterfall} if waterfall else {}),
        },
        "error": None,
        "created_at": row["created_at"],
        "duration_s": row["duration_s"],
    }


# ── Settings ──────────────────────────────────────────────────────────────

def get_settings() -> dict:
    """Return all settings as a flat dict. Returns {} if none saved yet."""
    if not _conn:
        return {}
    rows = _conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: json.loads(r["value"]) for r in rows}


def save_settings(settings: dict) -> None:
    """Upsert every key/value pair in *settings* into the settings table."""
    if not _conn:
        return
    with _lock:
        _conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(k, json.dumps(v)) for k, v in settings.items()],
        )
        _conn.commit()
    logger.info("Settings saved (%d keys)", len(settings))


def update_scan_note(scan_id: str, note: str) -> dict | None:
    if not _conn:
        return None
    with _lock:
        cur = _conn.execute("UPDATE scans SET note = ? WHERE id = ?", (note, scan_id))
        _conn.commit()
    if cur.rowcount == 0:
        return None
    return get_scan(scan_id)


def list_saved_frequencies(limit: int = 200) -> list[dict]:
    if not _conn:
        return []
    rows = _conn.execute(
        """SELECT id, freq_mhz, description, scan_id, preset_band, created_at
           FROM saved_frequencies
           ORDER BY created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_frequency(freq_mhz: float, description: str,
                   scan_id: str | None = None,
                   preset_band: str | None = None) -> dict | None:
    if not _conn:
        return None
    from datetime import datetime, timezone

    created_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        cur = _conn.execute(
            """INSERT INTO saved_frequencies (freq_mhz, description, scan_id, preset_band, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (freq_mhz, description, scan_id, preset_band, created_at),
        )
        _conn.commit()
    row = _conn.execute(
        "SELECT id, freq_mhz, description, scan_id, preset_band, created_at FROM saved_frequencies WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row) if row else None


def delete_saved_frequency(freq_id: int) -> bool:
    if not _conn:
        return False
    with _lock:
        cur = _conn.execute("DELETE FROM saved_frequencies WHERE id = ?", (freq_id,))
        _conn.commit()
    return cur.rowcount > 0

