"""Normalized reading contract: UTC timestamp, aggregate watts, optional truth.

Blank means unknown, never off. Replay pacing does not change source time.
"""
import csv
import io
import math
from datetime import datetime, timezone

DEVICE_IDS = ("lamp", "refrigerator", "microwave")
MAX_BYTES = 5_000_000
MAX_ROWS = 50_000
MAX_WATTS = 1_000_000  # Conservative numeric safety bound, not a detection range.


def parse_csv(text):
    try:
        return _parse_csv(text)
    except csv.Error as exc:
        raise ValueError(f'Malformed CSV: {exc}') from exc


def _parse_csv(text):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV exceeds the 5 MB limit")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    if not reader.fieldnames or not {"timestamp", "total_watts"} <= set(reader.fieldnames):
        raise ValueError("CSV requires timestamp and total_watts columns")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Duplicate CSV column names")
    rows, previous = [], None
    for line, raw in enumerate(reader, 2):
        if len(rows) >= MAX_ROWS:
            raise ValueError("CSV exceeds the 50,000 reading limit")
        try:
            timestamp = datetime.fromisoformat(raw["timestamp"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("timestamps need a timezone, e.g. Z or +00:00")
            timestamp = timestamp.astimezone(timezone.utc)
            if previous is not None and timestamp <= previous:
                raise ValueError("timestamps must increase; split households into separate files")
            row = {"timestamp": timestamp.isoformat()}
            keys = ("total_watts", *DEVICE_IDS, *(['washing_machine'] if 'washing_machine' in reader.fieldnames else []))
            for key in keys:
                value = raw.get(key)
                row[key] = None if value is None or not value.strip() else float(value)
                if row[key] is not None and (not math.isfinite(row[key]) or not 0 <= row[key] <= MAX_WATTS):
                    raise ValueError(f"{key} must be finite and between 0 and {MAX_WATTS} watts; net export is unsupported")
            if None in raw:
                raise ValueError("too many columns")
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            raise ValueError(f"CSV line {line}: {exc}") from exc
        rows.append(row)
        previous = timestamp
    if len(rows) < 2:
        raise ValueError("Provide at least two readings")
    return rows


def seconds_between(current, previous):
    return (datetime.fromisoformat(current["timestamp"]) -
            datetime.fromisoformat(previous["timestamp"])).total_seconds()


def valid_interval(current, previous, cadence):
    """Never integrate or create windows across gaps larger than 1.5× cadence."""
    if previous is None or current["total_watts"] is None or previous["total_watts"] is None:
        return 0.0
    dt = seconds_between(current, previous)
    return dt if 0 < dt <= cadence * 1.5 else 0.0


def regular_interval(current, previous, cadence):
    """Feature windows require cadence within 20%; energy can use shorter intervals."""
    return previous is not None and abs(seconds_between(current, previous) - cadence) <= cadence * .2
