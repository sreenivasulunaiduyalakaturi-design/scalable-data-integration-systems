import csv
from .base import Source


class CSVSource(Source):
    def read_batches(self, batch_size):
        with open(self.spec["path"], newline="", encoding="utf-8") as fh:
            batch = []
            for row in csv.DictReader(fh):
                batch.append(row)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
