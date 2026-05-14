"""
scheduler.py — finds free slots and handles task collisions.
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import re


# Priority map: higher number = higher priority
PRIORITY_KEYWORDS = {
    "exam": 10, "interview": 10, "meeting": 9, "call": 8,
    "doctor": 9, "appointment": 9, "deadline": 9,
    "study": 5, "work": 6, "exercise": 4, "gym": 4,
    "read": 3, "relax": 2, "break": 2,
}


def get_priority(title: str) -> int:
    """Return priority score for a task title."""
    title_lower = title.lower()
    for keyword, priority in PRIORITY_KEYWORDS.items():
        if keyword in title_lower:
            return priority
    return 5  # default medium priority


def resolve_day(day_str: str) -> datetime:
    """Convert natural day strings to a concrete date."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    day_lower = day_str.lower().strip()

    if day_lower in ("today", ""):
        return today
    if day_lower == "tomorrow":
        return today + timedelta(days=1)

    # Handle weekday names
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day_lower in weekdays:
        target_wd = weekdays.index(day_lower)
        current_wd = today.weekday()
        delta = (target_wd - current_wd) % 7
        delta = delta if delta > 0 else 7
        return today + timedelta(days=delta)

    # Try parsing ISO date
    try:
        return datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError:
        pass

    return today + timedelta(days=1)  # fallback: tomorrow


def resolve_start_time(day: datetime, preferred_time: str) -> datetime:
    """Convert a preferred time string to a concrete datetime."""
    time_lower = preferred_time.lower().strip()

    # Named periods
    if time_lower in ("morning", "am"):
        return day.replace(hour=9, minute=0)
    if time_lower in ("afternoon",):
        return day.replace(hour=14, minute=0)
    if time_lower in ("evening",):
        return day.replace(hour=18, minute=0)
    if time_lower in ("night",):
        return day.replace(hour=20, minute=0)

    # HH:MM format
    match = re.match(r"(\d{1,2}):(\d{2})", time_lower)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        return day.replace(hour=hour, minute=minute)

    # Plain hour like "5pm", "9am"
    match = re.match(r"(\d{1,2})(am|pm)?", time_lower)
    if match:
        hour = int(match.group(1))
        period = match.group(2)
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        return day.replace(hour=hour, minute=0)

    # Default to 9am
    return day.replace(hour=9, minute=0)


def find_free_slot(
    desired_start: datetime,
    duration_minutes: int,
    existing_events: List[Tuple[datetime, datetime, str]],  # (start, end, title)
) -> Tuple[datetime, datetime, Optional[str]]:
    """
    Try to place a task at desired_start.
    If blocked, slide forward in 15-min increments (max 8 hours).
    Returns (start, end, note).
    """
    duration = timedelta(minutes=duration_minutes)
    candidate = desired_start
    max_attempts = 32  # 32 * 15 min = 8 hours

    for _ in range(max_attempts):
        candidate_end = candidate + duration
        conflict = None
        for ev_start, ev_end, ev_title in existing_events:
            # Overlap check
            if candidate < ev_end and candidate_end > ev_start:
                conflict = (ev_start, ev_end, ev_title)
                break
        if conflict is None:
            note = None if candidate == desired_start else f"Shifted to {candidate.strftime('%H:%M')} due to conflicts"
            return candidate, candidate_end, note
        # Slide past the conflicting event
        candidate = conflict[1]

    # Could not find a slot — return desired anyway with a warning
    return desired_start, desired_start + duration, "⚠️ Could not find a free slot; placed at original time"


def check_and_shift(
    title: str,
    desired_start: datetime,
    duration_minutes: int,
    existing_events: List[Tuple[datetime, datetime, str]],
) -> Tuple[datetime, datetime, str, Optional[str]]:
    """
    High-level scheduler: finds a slot and returns
    (start, end, status, note).
    Status is 'scheduled' | 'shifted'.
    """
    start, end, note = find_free_slot(desired_start, duration_minutes, existing_events)
    status = "shifted" if note and "Shifted" in note else "scheduled"
    return start, end, status, note