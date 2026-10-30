from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _first_weekday(year: int, month: int, weekday: int, hour: int = 0) -> datetime:
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.replace(hour=hour)


def _dst_start(year: int) -> datetime:
    first = _first_weekday(year, 3, 6)
    # second Sunday; DST starts at 10:00 UTC
    return (first + timedelta(days=7)).replace(hour=10, minute=0)


def _dst_end(year: int) -> datetime:
    first = _first_weekday(year, 11, 6)
    return first.replace(hour=9, minute=0)


def pacific_offset_hours(utc: datetime) -> int:
    value = utc if utc.tzinfo is not None else utc.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    year = value.year
    start = _dst_start(year)
    end = _dst_end(year)
    return -7 if start <= value < end else -8


def pacific_day_key(utc: datetime) -> str:
    value = utc if utc.tzinfo is not None else utc.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    offset = pacific_offset_hours(value)
    return (value + timedelta(hours=offset)).strftime("%Y-%m-%d")


def next_pacific_midnight(utc: datetime) -> datetime:
    value = utc if utc.tzinfo is not None else utc.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    local_key = pacific_day_key(value)
    year, month, day = map(int, local_key.split("-"))
    # Find the next local midnight by adding one local calendar day.
    next_local = datetime(year, month, day, tzinfo=timezone.utc) + timedelta(days=1)
    candidate = next_local.replace(hour=0)
    offset = pacific_offset_hours(value)
    return candidate - timedelta(hours=offset)
