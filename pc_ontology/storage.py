"""Local user library. OWL remains the source of hardware facts.

Only user configuration, prices and JSON snapshots are stored in SQLite.
Connections are short-lived, transactions atomic, archived records recoverable.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from .schema import ROOT


def default_path():
    folder = Path(os.environ.get("PC_ONTOLOGY_DATA_DIR", str(ROOT / "data")))
    return folder / "contour.sqlite3"


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
    def __init__(self, path=None):
        self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False) if str(path) == ":memory:" else None
        self.path = Path(path) if path is not None else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("Сохранения созданы более новой версией приложения.")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS builds (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, notes TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1))
                );
                CREATE TABLE IF NOT EXISTS prices (
                    component_id TEXT PRIMARY KEY, price INTEGER NOT NULL CHECK(typeof(price)='integer' AND price>=0),
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        conn = self._memory_connection if self._memory_connection is not None else sqlite3.connect(str(self.path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            if self._memory_connection is None:
                conn.close()

    @staticmethod
    def _payload(payload):
        if not isinstance(payload, dict) or payload.get("format") != "pc-ontology-build":
            raise ValueError("Некорректный снимок сборки.")
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)

    def save_build(self, title, payload, notes="", id=None):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise ValueError("Название должно содержать от 1 до 100 символов.")
        if not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError("Заметка должна быть не длиннее 4000 символов.")
        body, now = self._payload(payload), timestamp()
        with self.connection() as conn:
            if id is None:
                id = uuid4().hex
                conn.execute("INSERT INTO builds VALUES(?,?,?,?,?,?,0)",
                             (id, title.strip(), notes, now, now, body))
            else:
                changed = conn.execute("UPDATE builds SET title=?,notes=?,updated_at=?,payload=? WHERE id=? AND archived=0",
                                       (title.strip(), notes, now, body, id)).rowcount
                if not changed:
                    raise KeyError("Сохранённая сборка не найдена или находится в архиве.")
        return id

    def list_builds(self, archived=False):
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT id,title,notes,created_at,updated_at FROM builds WHERE archived=? ORDER BY updated_at DESC,id",
                (int(archived),))]

    def load_build(self, id):
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM builds WHERE id=?", (id,)).fetchone()
        if row is None:
            raise KeyError("Сборка не найдена.")
        record = dict(row)
        record["payload"] = json.loads(record["payload"])
        return record

    def archive(self, id, archived=True):
        with self.connection() as conn:
            if not conn.execute("UPDATE builds SET archived=?,updated_at=? WHERE id=?",
                                (int(archived), timestamp(), id)).rowcount:
                raise KeyError("Сборка не найдена.")

    def prices(self):
        with self.connection() as conn:
            return {row["component_id"]: row["price"] for row in conn.execute("SELECT * FROM prices")}

    def update_prices(self, updates):
        if not isinstance(updates, dict) or any(not isinstance(k, str) or not k or
                (v is not None and (type(v) is not int or v < 0 or v > 1_000_000_000))
                for k, v in updates.items()):
            raise ValueError("Цена должна быть целым числом от 0 до 1 000 000 000 либо пустым значением.")
        now = timestamp()
        with self.connection() as conn:
            for id, value in updates.items():
                if value is None:
                    conn.execute("DELETE FROM prices WHERE component_id=?", (id,))
                else:
                    conn.execute("INSERT INTO prices VALUES(?,?,?) ON CONFLICT(component_id) DO UPDATE SET price=excluded.price,updated_at=excluded.updated_at",
                                 (id, value, now))

    def load_draft(self):
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='draft'").fetchone()
        return json.loads(row[0]) if row else None

    def save_draft(self, payload):
        body = self._payload(payload)
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='draft'").fetchone()
            if row and row[0] == body:
                return False
            conn.execute("INSERT INTO settings VALUES('draft',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                         (body, timestamp()))
        return True
