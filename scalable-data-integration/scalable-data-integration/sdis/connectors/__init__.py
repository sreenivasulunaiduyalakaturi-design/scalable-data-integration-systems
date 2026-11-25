from .csv_source import CSVSource
from .json_source import JSONSource
from .sqlite_source import SQLiteSource

REGISTRY = {"csv": CSVSource, "json": JSONSource, "sqlite": SQLiteSource}


def build_source(spec: dict):
    """Factory: add a new connector by registering it in REGISTRY."""
    try:
        return REGISTRY[spec["type"]](spec)
    except KeyError:
        raise ValueError(f"Unknown source type: {spec.get('type')!r}. Available: {list(REGISTRY)}")
