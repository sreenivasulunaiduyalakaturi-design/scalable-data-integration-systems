import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sdis.pipeline import run_pipeline  # noqa: E402
from sdis.transform import RecordError, transform_record  # noqa: E402


class TransformTests(unittest.TestCase):
    MAP = {"email": {"from": "e", "type": "email", "required": True},
           "d": {"from": "d", "type": "date"}}

    def test_normalises(self):
        r = transform_record({"e": " A@B.com ", "d": "25/12/2024"}, self.MAP, "x")
        self.assertEqual(r["email"], "a@b.com")
        self.assertEqual(r["d"], "2024-12-25")

    def test_rejects_bad_email(self):
        with self.assertRaises(RecordError):
            transform_record({"e": "nope", "d": "2024-01-01"}, self.MAP, "x")


class PipelineTests(unittest.TestCase):
    def _cfg(self, tmp, records):
        src = os.path.join(tmp, "in.jsonl")
        with open(src, "w") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
        return {"target": {"database": os.path.join(tmp, "w.db")}, "batch_size": 2, "workers": 2,
                "datasets": [{"name": "t", "table": "t", "key": ["id"],
                              "columns": {"id": "TEXT", "v": "INTEGER"},
                              "sources": [{"type": "json", "system": "s", "path": src, "mapping": {
                                  "id": {"from": "id", "type": "str", "required": True},
                                  "v": {"from": "v", "type": "int"}}}]}]}

    def test_end_to_end_upsert_and_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._cfg(tmp, [{"id": "1", "v": "5"}, {"id": "1", "v": "9"},
                                  {"id": "2", "v": "x"}, {"id": "3", "v": "2"}])
            m = run_pipeline(cfg)[0]
            self.assertEqual((m.read, m.rejected), (4, 1))
            conn = sqlite3.connect(cfg["target"]["database"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT v FROM t WHERE id='1'").fetchone()[0], 9)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM rejects").fetchone()[0], 1)
            conn.close()

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._cfg(tmp, [{"id": "1", "v": "5"}])
            run_pipeline(cfg)
            run_pipeline(cfg)
            conn = sqlite3.connect(cfg["target"]["database"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
