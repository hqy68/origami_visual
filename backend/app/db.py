"""SQLite catalog of scraped models. Stores metadata and links back to the source;
we do not copy diagram images or tutorial text onto our own servers."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

DB_PATH = Path(os.environ.get("ORIGAMI_DB", Path(__file__).resolve().parent.parent / "data" / "catalog.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    designer TEXT,
    kind TEXT NOT NULL,            -- 'crease_pattern' or 'tutorial'
    difficulty TEXT,
    description TEXT,
    image_url TEXT,                -- hotlinked thumbnail, shown with attribution
    tags TEXT NOT NULL DEFAULT '[]',
    license_note TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS takedowns (
    url TEXT PRIMARY KEY,
    requested_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def connect(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    p = Path(path or DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_model(conn: sqlite3.Connection, record: dict) -> None:
    blocked = conn.execute("SELECT 1 FROM takedowns WHERE url = ?", (record["url"],)).fetchone()
    if blocked:
        return
    conn.execute(
        """
        INSERT INTO models (source, url, title, designer, kind, difficulty, description,
                            image_url, tags, license_note)
        VALUES (:source, :url, :title, :designer, :kind, :difficulty, :description,
                :image_url, :tags, :license_note)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title, designer=excluded.designer, kind=excluded.kind,
            difficulty=excluded.difficulty, description=excluded.description,
            image_url=excluded.image_url, tags=excluded.tags,
            license_note=excluded.license_note, fetched_at=datetime('now')
        """,
        {
            "designer": None, "difficulty": None, "description": None,
            "image_url": None, "license_note": None,
            **record,
            "tags": json.dumps(record.get("tags", [])),
        },
    )


def add_takedown(conn: sqlite3.Connection, url: str) -> None:
    conn.execute("INSERT OR IGNORE INTO takedowns (url) VALUES (?)", (url,))
    conn.execute("DELETE FROM models WHERE url = ?", (url,))


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    return d


def all_models(conn: sqlite3.Connection) -> List[dict]:
    return [row_to_dict(r) for r in conn.execute("SELECT * FROM models")]


def get_model(conn: sqlite3.Connection, model_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    return row_to_dict(row) if row else None
