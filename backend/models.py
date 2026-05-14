from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskRequest(BaseModel):
    natural_language: str  # e.g. "Study ML tomorrow at 5pm for 2 hours"


class ParsedTask(BaseModel):
    title: str
    duration_minutes: int
    day: str           # e.g. "tomorrow", "monday", "2025-06-10"
    preferred_time: str  # e.g. "17:00", "morning", "afternoon"


class ScheduledTask(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    calendar_event_link: Optional[str] = None
    status: str = "scheduled"   # "scheduled" | "shifted" | "conflict"
    note: Optional[str] = None


class ScheduleResponse(BaseModel):
    success: bool
    task: Optional[ScheduledTask] = None
    message: str


class FocusSessionStatus(BaseModel):
    active: bool
    elapsed_seconds: int
    remaining_seconds: int
    distraction_warnings: int