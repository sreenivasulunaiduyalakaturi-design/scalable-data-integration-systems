"""Schema mapping, cleaning and validation.

Top-level functions only (picklable) so batches can run in a process pool.
"""
import re
from datetime import datetime
from typing import Dict, List, Tuple

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d %b %Y", "%Y-%m-%dT%H:%M:%S")


class RecordError(ValueError):
    """Raised when a record cannot be mapped / validated."""


def _cast(value, type_: str):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if type_ == "str":
        return str(value).strip()
    if type_ == "int":
        return int(float(str(value).replace(",", "")))
    if type_ == "float":
        return round(float(str(value).replace(",", "")), 4)
    if type_ == "email":
        v = str(value).strip().lower()
        if not EMAIL_RE.match(v):
            raise RecordError(f"invalid email: {value!r}")
        return v
    if type_ == "date":
        s = str(value).strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        raise RecordError(f"unparseable date: {value!r}")
    raise RecordError(f"unknown type {type_!r}")


def transform_record(raw: Dict, mapping: Dict, system: str) -> Dict:
    out = {}
    for target, rule in mapping.items():
        value = raw.get(rule["from"])
        try:
            value = _cast(value, rule.get("type", "str"))
        except RecordError:
            raise
        except (ValueError, TypeError) as exc:
            raise RecordError(f"{target}: {exc}")
        if value is None:
            value = rule.get("default")
        if value is None and rule.get("required"):
            raise RecordError(f"missing required field: {target}")
        if isinstance(value, str):
            if rule.get("case") == "upper":
                value = value.upper()
            elif rule.get("case") == "lower":
                value = value.lower()
            elif rule.get("case") == "title":
                value = value.title()
        if "min" in rule and value is not None and value < rule["min"]:
            raise RecordError(f"{target}: {value} below minimum {rule['min']}")
        out[target] = value
    out["source_system"] = system
    return out


def transform_batch(batch: List[Dict], mapping: Dict, system: str) -> Tuple[List[Dict], List[Dict]]:
    """Returns (good_records, rejects)."""
    good, bad = [], []
    for raw in batch:
        try:
            good.append(transform_record(raw, mapping, system))
        except RecordError as exc:
            bad.append({"reason": str(exc), "raw": raw})
    return good, bad
