"""SQLite stores readings on disk so closing the browser cannot lose them."""

import sqlite3
import json
from contextlib import closing


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            # A CSV reader can stay open while the simulator keeps writing.
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL NOT NULL)")
            db.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY,
                    session TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    second INTEGER NOT NULL,
                    total_watts REAL NOT NULL,
                    lamp REAL NOT NULL,
                    refrigerator REAL NOT NULL,
                    microwave REAL NOT NULL,
                    actual_mask INTEGER NOT NULL,
                    predicted_mask INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    energy_kwh REAL NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS session_id ON readings(session, id)")
            # Additive migration: preserve the original table and every legacy ID.
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='readings_v2'").fetchone()
            db.execute("""CREATE TABLE IF NOT EXISTS readings_v2 (
                id INTEGER PRIMARY KEY, session TEXT NOT NULL, timestamp TEXT NOT NULL,
                second REAL NOT NULL, total_watts REAL, lamp REAL, refrigerator REAL,
                microwave REAL, actual_mask INTEGER, predicted_mask INTEGER, confidence REAL,
                energy_kwh REAL NOT NULL, source TEXT NOT NULL DEFAULT 'simulator',
                quality TEXT NOT NULL DEFAULT 'legacy', prediction_quality TEXT DEFAULT 'legacy',
                interval_seconds REAL NOT NULL DEFAULT 1, model_version TEXT DEFAULT 'legacy',
                unexplained_watts REAL, predictions TEXT NOT NULL DEFAULT '{}', source_id TEXT
            )""")
            if not exists:
                db.execute("""INSERT INTO readings_v2
                    (id,session,timestamp,second,total_watts,lamp,refrigerator,microwave,
                     actual_mask,predicted_mask,confidence,energy_kwh)
                    SELECT id,session,timestamp,second,total_watts,lamp,refrigerator,microwave,
                     actual_mask,predicted_mask,confidence,energy_kwh FROM readings""")
            db.execute("CREATE INDEX IF NOT EXISTS session_v2_id ON readings_v2(session, id)")
            columns = {row['name'] for row in db.execute('PRAGMA table_info(readings_v2)')}
            if 'source_id' not in columns:
                db.execute('ALTER TABLE readings_v2 ADD COLUMN source_id TEXT')
            if 'washing_machine' not in columns:
                db.execute('ALTER TABLE readings_v2 ADD COLUMN washing_machine REAL')
            if 'washing_machine_stage' not in columns:
                db.execute('ALTER TABLE readings_v2 ADD COLUMN washing_machine_stage TEXT')

    def connect(self):
        # Streaming responses may resume on different worker threads, serially.
        db = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def save(self, reading):
        reading = {**reading, "predictions": json.dumps(reading.get("predictions", {}))}
        columns = list(reading)
        query = f"INSERT INTO readings_v2 ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
        with closing(self.connect()) as db, db:
            cursor = db.execute(query, list(reading.values()))
            return cursor.lastrowid

    def history(self, session, limit=300, after_id=0):
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT * FROM readings_v2 WHERE session = ? AND id > ? ORDER BY id DESC LIMIT ?",
                (session, after_id, limit),
            ).fetchall()
        return [self.decode(row) for row in reversed(rows)]

    @staticmethod
    def decode(row):
        return {**dict(row), "predictions": json.loads(row["predictions"])}

    def get_rate(self):
        with closing(self.connect()) as db:
            row = db.execute("SELECT value FROM settings WHERE key = 'rate'").fetchone()
        return float(row[0]) if row else 0.16

    def set_rate(self, rate):
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO settings(key, value) VALUES ('rate', ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (rate,))

    def export_rows(self):
        with closing(self.connect()) as db:
            for row in db.execute("SELECT * FROM readings_v2 ORDER BY id"):
                yield self.decode(row)

    def sessions(self, limit=20):
        with closing(self.connect()) as db:
            rows = db.execute('''SELECT session, source, COUNT(*) AS samples,
                MIN(timestamp) AS first_timestamp, MAX(timestamp) AS last_timestamp,
                MAX(energy_kwh) AS energy_kwh, SUM(interval_seconds) AS covered_seconds,
                SUM(CASE WHEN quality = 'missing' THEN 1 ELSE 0 END) AS missing_rows,
                SUM(CASE WHEN quality = 'gap' THEN 1 ELSE 0 END) AS gap_rows
                FROM readings_v2 GROUP BY session, source ORDER BY MAX(id) DESC LIMIT ?''', (limit,)).fetchall()
        return [dict(row) for row in rows]
