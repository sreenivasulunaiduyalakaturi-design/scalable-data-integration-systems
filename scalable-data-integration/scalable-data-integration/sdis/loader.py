import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List


class WarehouseLoader:
    """Loads records into a SQLite 'warehouse' using idempotent upserts."""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS rejects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, dataset TEXT, source_system TEXT,
                reason TEXT, raw TEXT, rejected_at TEXT)"""
        )
        self.conn.commit()

    def ensure_table(self, table: str, columns: Dict[str, str], key: List[str]):
        cols = ", ".join(f"{c} {t}" for c, t in columns.items())
        cols += ", source_system TEXT, ingested_at TEXT"
        pk = ", ".join(key)
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({cols}, PRIMARY KEY ({pk}))")
        self.conn.commit()

    def upsert(self, table: str, columns: List[str], key: List[str], records: List[Dict]) -> int:
        if not records:
            return 0
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        all_cols = columns + ["source_system", "ingested_at"]
        placeholders = ", ".join("?" for _ in all_cols)
        # COALESCE: a newer record only overwrites a field when it actually has a value,
        # so two systems describing the same entity get merged rather than clobbered.
        updates = ", ".join(
            f"{c}=COALESCE(excluded.{c}, {table}.{c})" for c in all_cols if c not in key
        )
        sql = (
            f"INSERT INTO {table} ({', '.join(all_cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT({', '.join(key)}) DO UPDATE SET {updates}"
        )
        rows = [tuple(r.get(c) for c in columns) + (r["source_system"], now) for r in records]
        with self.conn:
            self.conn.executemany(sql, rows)
        return len(rows)

    def save_rejects(self, dataset: str, system: str, rejects: List[Dict]):
        if not rejects:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.conn:
            self.conn.executemany(
                "INSERT INTO rejects (dataset, source_system, reason, raw, rejected_at) VALUES (?,?,?,?,?)",
                [(dataset, system, r["reason"], json.dumps(r["raw"], default=str), now) for r in rejects],
            )

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def close(self):
        self.conn.close()
