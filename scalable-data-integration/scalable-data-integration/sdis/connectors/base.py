from abc import ABC, abstractmethod
from typing import Dict, Iterator, List


class Source(ABC):
    """Every data source yields batches (lists of dict records).

    Streaming in batches keeps memory flat no matter how large the source is.
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.system = spec.get("system", spec.get("type", "unknown"))

    @abstractmethod
    def read_batches(self, batch_size: int) -> Iterator[List[Dict]]:
        ...
