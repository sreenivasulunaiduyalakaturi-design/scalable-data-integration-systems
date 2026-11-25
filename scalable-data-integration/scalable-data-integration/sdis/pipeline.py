import json
import logging
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List

from .connectors import build_source
from .loader import WarehouseLoader
from .transform import transform_batch

log = logging.getLogger("sdis")


@dataclass
class Metrics:
    dataset: str
    read: int = 0
    loaded: int = 0
    rejected: int = 0
    seconds: float = 0.0
    by_source: Dict[str, int] = field(default_factory=dict)

    @property
    def throughput(self) -> float:
        return self.read / self.seconds if self.seconds else 0.0


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_pipeline(config: dict) -> List[Metrics]:
    batch_size = config.get("batch_size", 1000)
    workers = config.get("workers", 4)
    executor_cls = ProcessPoolExecutor if config.get("executor") == "process" else ThreadPoolExecutor

    loader = WarehouseLoader(config["target"]["database"])
    results: List[Metrics] = []
    try:
        with executor_cls(max_workers=workers) as pool:
            for ds in config["datasets"]:
                results.append(_run_dataset(ds, loader, pool, batch_size, workers))
    finally:
        loader.close()
    return results


def _run_dataset(ds: dict, loader: WarehouseLoader, pool, batch_size: int, workers: int) -> Metrics:
    name, table, key = ds["name"], ds["table"], ds["key"]
    columns = list(ds["columns"])
    loader.ensure_table(table, ds["columns"], key)
    m = Metrics(dataset=name)
    start = time.perf_counter()

    for spec in ds["sources"]:
        source = build_source(spec)
        mapping = spec["mapping"]
        log.info("[%s] reading source '%s' (%s)", name, source.system, spec["type"])
        in_flight = deque()  # bounded window => back-pressure, constant memory

        def drain_one():
            batch_len, fut = in_flight.popleft()
            good, bad = fut.result()
            m.read += batch_len
            m.loaded += loader.upsert(table, columns, key, good)
            m.rejected += len(bad)
            m.by_source[source.system] = m.by_source.get(source.system, 0) + len(good)
            loader.save_rejects(name, source.system, bad)

        for batch in source.read_batches(batch_size):
            in_flight.append((len(batch), pool.submit(transform_batch, batch, mapping, source.system)))
            if len(in_flight) >= workers * 2:
                drain_one()
        while in_flight:
            drain_one()

    m.seconds = time.perf_counter() - start
    log.info("[%s] read=%d loaded=%d rejected=%d table_rows=%d (%.0f rec/s)",
             name, m.read, m.loaded, m.rejected, loader.count(table), m.throughput)
    return m
