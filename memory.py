# -*- coding: utf-8 -*-
"""Vicky Talk local memory — personal data stays on this machine.

SQLite database (default: %HOME%/.vickytalk/memory.db) holding:
  * facts      — remembered key/value pairs
  * objectives — WORK / PERSONAL goals with status + progress
  * reminders  — time-based reminders checked by reminders.ReminderService

Thread-safe via a lock (check_same_thread=False). Never raises on
construction; DB errors surface from methods only where unavoidable.
"""

import sqlite3
import threading
from pathlib import Path

try:
    from app_name import APP_NAME
except Exception:
    APP_NAME = "Vicky Talk"

DEFAULT_DB_PATH = Path.home() / (".%s" % APP_NAME.lower().replace(" ", "")) / "memory.db"


class Memory:
    """Local SQLite store for facts, objectives and reminders."""

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ---------------------------------------------------------------- schema
    def _init_schema(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS facts ("
                "key TEXT PRIMARY KEY, value TEXT)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS objectives ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "title TEXT, tag TEXT DEFAULT 'WORK', "
                "status TEXT DEFAULT 'pending', progress INTEGER DEFAULT 0)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS reminders ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "text TEXT, due_ts REAL, done INTEGER DEFAULT 0)"
            )
            self._conn.commit()

    # ----------------------------------------------------------------- facts
    def add_fact(self, key, value):
        """Store or overwrite a remembered fact."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO facts (key, value) VALUES (?, ?)",
                (str(key), str(value)),
            )
            self._conn.commit()

    def get_fact(self, key):
        """Return the fact's value, or None if unknown."""
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM facts WHERE key = ?", (str(key),)
            ).fetchone()
            return row["value"] if row else None

    def all_facts(self):
        """Return all facts as a dict."""
        with self._lock:
            rows = self._conn.execute("SELECT key, value FROM facts").fetchall()
            return {r["key"]: r["value"] for r in rows}

    # ------------------------------------------------------------ objectives
    def add_objective(self, title, tag="WORK"):
        """Add an objective; returns its integer id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO objectives (title, tag) VALUES (?, ?)",
                (str(title), str(tag).upper()),
            )
            self._conn.commit()
            return cur.lastrowid

    def list_objectives(self, status=None):
        """Return objectives as list of dicts, optionally filtered by status."""
        with self._lock:
            if status is None:
                rows = self._conn.execute(
                    "SELECT id, title, tag, status, progress "
                    "FROM objectives ORDER BY id"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, title, tag, status, progress FROM objectives "
                    "WHERE status = ? ORDER BY id",
                    (status,),
                ).fetchall()
            return [dict(r) for r in rows]

    def update_objective(self, id, status=None, progress=None):
        """Update status and/or progress (0-100) of an objective."""
        sets, vals = [], []
        if status is not None:
            sets.append("status = ?")
            vals.append(str(status))
        if progress is not None:
            try:
                p = max(0, min(100, int(progress)))
            except (TypeError, ValueError):
                p = 0
            sets.append("progress = ?")
            vals.append(p)
        if not sets:
            return
        vals.append(id)
        with self._lock:
            self._conn.execute(
                "UPDATE objectives SET %s WHERE id = ?" % ", ".join(sets), vals
            )
            self._conn.commit()

    def delete_objective(self, id):
        """Delete an objective by id."""
        with self._lock:
            self._conn.execute("DELETE FROM objectives WHERE id = ?", (id,))
            self._conn.commit()

    # ------------------------------------------------------------- reminders
    def add_reminder(self, text, due_ts):
        """Add a reminder due at due_ts (epoch seconds); returns its id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO reminders (text, due_ts) VALUES (?, ?)",
                (str(text), float(due_ts)),
            )
            self._conn.commit()
            return cur.lastrowid

    def due_reminders(self, now_ts):
        """Return not-yet-done reminders whose due time has passed."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, due_ts, done FROM reminders "
                "WHERE done = 0 AND due_ts <= ? ORDER BY due_ts",
                (float(now_ts),),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_reminder_done(self, id):
        """Mark a reminder as delivered."""
        with self._lock:
            self._conn.execute(
                "UPDATE reminders SET done = 1 WHERE id = ?", (id,)
            )
            self._conn.commit()

    # ------------------------------------------------------------------ misc
    def close(self):
        """Close the database connection."""
        with self._lock:
            self._conn.close()
