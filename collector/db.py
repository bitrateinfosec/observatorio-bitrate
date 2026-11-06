"""Capa de persistencia (SQLite). El archivo .db se commitea al repo
para que GitHub Actions conserve el histórico entre corridas."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS victims (
    id            TEXT PRIMARY KEY,      -- hash estable (grupo + nombre)
    name          TEXT NOT NULL,
    group_name    TEXT NOT NULL,
    sector        TEXT,
    website       TEXT,
    country       TEXT,
    published     TEXT,                  -- fecha en que el grupo lo publicó
    discovered    TEXT,                  -- fecha en que la fuente lo detectó
    source        TEXT NOT NULL,
    first_seen    TEXT NOT NULL,         -- cuándo lo vio el observatorio
    alerted       INTEGER DEFAULT 0,
    hidden        INTEGER DEFAULT 0      -- 1 = baja/corrección solicitada
);

CREATE TABLE IF NOT EXISTS iocs (
    id            TEXT PRIMARY KEY,      -- fuente:valor
    value         TEXT NOT NULL,
    ioc_type      TEXT NOT NULL,         -- ip:port, url, domain, ip
    threat        TEXT,                  -- botnet_cc, payload_delivery...
    malware       TEXT,
    ip            TEXT,
    asn           INTEGER,
    as_name       TEXT,
    country       TEXT,
    reason        TEXT,                  -- por qué se considera "AR"
    source        TEXT NOT NULL,
    reference     TEXT,
    first_seen    TEXT,
    collected_at  TEXT NOT NULL,
    alerted       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    source        TEXT NOT NULL,
    status        TEXT NOT NULL,         -- ok | skipped | error
    fetched       INTEGER DEFAULT 0,
    new_items     INTEGER DEFAULT 0,
    message       TEXT
);

CREATE INDEX IF NOT EXISTS idx_victims_published ON victims(published);
CREATE INDEX IF NOT EXISTS idx_iocs_first_seen ON iocs(first_seen);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_victim(conn, v: dict) -> bool:
    """Inserta una víctima. Devuelve True si es nueva."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO victims
           (id, name, group_name, sector, website, country, published, discovered, source, first_seen)
           VALUES (:id, :name, :group_name, :sector, :website, :country, :published, :discovered, :source, :first_seen)""",
        {**v, "first_seen": now_iso()},
    )
    return cur.rowcount == 1


def upsert_ioc(conn, i: dict) -> bool:
    cur = conn.execute(
        """INSERT OR IGNORE INTO iocs
           (id, value, ioc_type, threat, malware, ip, asn, as_name, country, reason, source, reference, first_seen, collected_at)
           VALUES (:id, :value, :ioc_type, :threat, :malware, :ip, :asn, :as_name, :country, :reason, :source, :reference, :first_seen, :collected_at)""",
        {**i, "collected_at": now_iso()},
    )
    return cur.rowcount == 1


def log_run(conn, source, status, fetched=0, new_items=0, message=""):
    conn.execute(
        "INSERT INTO runs (started_at, source, status, fetched, new_items, message) VALUES (?,?,?,?,?,?)",
        (now_iso(), source, status, fetched, new_items, message[:500]),
    )
