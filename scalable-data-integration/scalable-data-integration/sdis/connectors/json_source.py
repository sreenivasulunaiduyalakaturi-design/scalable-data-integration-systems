import json
from .base import Source


class JSONSource(Source):
    """Reads JSON Lines (one object per line) or a JSON array file."""

    def _records(self):
        path = self.spec["path"]
        with open(path, encoding="utf-8") as fh:
            first = fh.read(1)
            fh.seek(0)
            if first == "[":
                yield from json.load(fh)
            else:
                for line in fh:
                    line = line.strip()
                    if line:
                        yield json.loads(line)

    def read_batches(self, batch_size):
        batch = []
        for rec in self._records():
            batch.append(rec)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
