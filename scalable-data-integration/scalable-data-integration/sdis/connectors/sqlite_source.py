import sqlite3
from .base import Source


class SQLiteSource(Source):
    """Reads from any SQL query against a SQLite database (e.g. a legacy system)."""

    def read_batches(self, batch_size):
        conn = sqlite3.connect(self.spec["path"])
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(self.spec["query"])
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                yield [dict(r) for r in rows]
        finally:
            conn.close()
