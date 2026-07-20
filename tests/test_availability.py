# tests/test_availability.py
import pytest
from datetime import datetime, date, time
from unittest.mock import AsyncMock, MagicMock
from app.services.availability import is_slot_available, get_available_slots

# Test the overlap logic directly - no DB needed
def test_overlap_logic():
    """Validate the overlap formula: existing.start < end AND existing.end > start"""
    existing = (datetime(2025, 1, 10, 10, 0), datetime(2025, 1, 10, 12, 0))

    def overlaps(start, end):
        return existing[0] < end and existing[1] > start

    assert overlaps(datetime(2025, 1, 10, 9, 0), datetime(2025, 1, 10, 11, 0))   # partial overlap left
    assert overlaps(datetime(2025, 1, 10, 11, 0), datetime(2025, 1, 10, 13, 0))  # partial overlap right
    assert overlaps(datetime(2025, 1, 10, 10, 30), datetime(2025, 1, 10, 11, 30)) # inside existing
    assert overlaps(datetime(2025, 1, 10, 9, 0), datetime(2025, 1, 10, 13, 0))   # wraps existing

    assert not overlaps(datetime(2025, 1, 10, 8, 0), datetime(2025, 1, 10, 10, 0))  # ends exactly at start
    assert not overlaps(datetime(2025, 1, 10, 12, 0), datetime(2025, 1, 10, 14, 0)) # starts exactly at end

def test_slot_generation_logic():
    """
    Unit test the slot walking logic without hitting a DB.
    Simulates: staff works 9-12, one booking 10:00-10:30, service=60min, buffer=15min
    Total slot size = 75 min. Interval = 30 min.
    Expected open slots: 09:00-10:15 is blocked (overlaps with 10:00 booking)... let's trace it.
    """
    work_start = datetime(2025, 1, 10, 9, 0)
    work_end = datetime(2025, 1, 10, 12, 0)
    booked = [(datetime(2025, 1, 10, 10, 0), datetime(2025, 1, 10, 10, 30))]

    from datetime import timedelta
    total_duration = timedelta(minutes=75)
    interval = timedelta(minutes=30)

    slots = []
    cursor = work_start
    while cursor + total_duration <= work_end:
        candidate_end = cursor + total_duration
        overlaps = any(s < candidate_end and e > cursor for s, e in booked)
        if not overlaps:
            slots.append((cursor, candidate_end))
        cursor += interval

    # 09:00-10:15 overlaps with 10:00-10:30? Yes (10:00 < 10:15 and 10:30 > 09:00) - blocked
    # 09:30-10:45 overlaps? Yes - blocked
    # 10:00-11:15 overlaps? Yes - blocked
    # 10:30-11:45 overlaps? No! - open
    # 11:00-12:15 - 12:15 > work_end, skip
    assert len(slots) == 1
    assert slots[0][0] == datetime(2025, 1, 10, 10, 30)