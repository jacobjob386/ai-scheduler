"""
main.py — FastAPI backend for AI Scheduler.
Run with: uvicorn main:app --reload --port 8000
"""

import os
import json
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import TaskRequest, ScheduleResponse, ScheduledTask
from scheduler import resolve_day, resolve_start_time, check_and_shift
from calendar_service import get_calendar_service, get_existing_events, create_calendar_event
import focus_guardian as fg

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="AI Scheduler API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


# ── Ollama NL parser ─────────────────────────────────────────────────────────

async def parse_task_with_ollama(natural_language: str):
    from models import ParsedTask
    prompt = f"""Extract scheduling info and return ONLY valid JSON. No markdown.

Task: "{natural_language}"

JSON structure:
{{
  "title": "short task name",
  "duration_minutes": <integer>,
  "day": "today|tomorrow|monday|...|YYYY-MM-DD",
  "preferred_time": "HH:MM or morning|afternoon|evening|night"
}}"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate",
                                  json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status()
            raw = r.json().get("response", "").strip().strip("```json").strip("```").strip()
            return ParsedTask(**json.loads(raw))
    except Exception:
        return _fallback_parse(natural_language)


def _fallback_parse(text: str):
    import re
    from models import ParsedTask
    title, duration, day, preferred_time = text, 60, "tomorrow", "09:00"
    m = re.search(r"for\s+(\d+)\s*(hour|hr|minute|min)", text, re.I)
    if m:
        val, unit = int(m.group(1)), m.group(2).lower()
        duration = val * 60 if "hour" in unit or "hr" in unit else val
    m = re.search(r"at\s+(\d{1,2}(?::\d{2})?(?:am|pm)?)", text, re.I)
    if m:
        preferred_time = m.group(1)
    for kw in ["today","tomorrow","monday","tuesday","wednesday","thursday","friday","saturday","sunday"]:
        if kw in text.lower():
            day = kw; break
    title = re.sub(
        r"\b(at\s+[\d:apm]+|for\s+\d+\s*(hour|hr|minute|min)s?|tomorrow|today|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        "", text, flags=re.I).strip(" ,.")
    return ParsedTask(title=title or text[:40], duration_minutes=duration,
                      day=day, preferred_time=preferred_time)


# ── Schedule endpoint ────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/schedule", response_model=ScheduleResponse)
async def schedule_task(request: TaskRequest):
    try:
        parsed        = await parse_task_with_ollama(request.natural_language)
        day_dt        = resolve_day(parsed.day)
        desired_start = resolve_start_time(day_dt, parsed.preferred_time)
        day_start = day_dt.replace(hour=0,  minute=0,  second=0)
        day_end   = day_dt.replace(hour=23, minute=59, second=59)
        try:
            service  = get_calendar_service()
            existing = get_existing_events(service, day_start, day_end)
        except Exception:
            existing, service = [], None
        start, end, status, note = check_and_shift(
            parsed.title, desired_start, parsed.duration_minutes, existing)
        calendar_link = None
        if service:
            try:
                calendar_link = create_calendar_event(
                    service, parsed.title, start, end,
                    description=f"Scheduled by AI Scheduler\nOriginal: {request.natural_language}")
            except Exception as cal_err:
                note = (note or "") + f" (Calendar sync failed: {cal_err})"
        task = ScheduledTask(title=parsed.title, start_time=start, end_time=end,
                             calendar_event_link=calendar_link, status=status, note=note)
        return ScheduleResponse(success=True, task=task, message="Task scheduled successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Focus Guardian endpoints ─────────────────────────────────────────────────

@app.post("/focus/start")
def start_focus():
    if fg.session_stats["active"]:
        return {"message": "Session already active"}
    fg.start_session()
    return {"message": "Focus session started — webcam is now monitoring"}


@app.post("/focus/stop")
def stop_focus():
    fg.stop_session()
    return {"message": "Focus session stopped"}


@app.get("/focus/status")
def focus_status():
    s = fg.session_stats
    return {
        "active":             s["active"],
        "elapsed_seconds":    s["elapsed_seconds"],
        "remaining_seconds":  s["remaining_seconds"],
        "focus_score":        s["focus_score"],
        "absent_events":      s["absent_events"],
        "look_away_events":   s["look_away_events"],
        "drowsy_events":      s["drowsy_events"],
        "distracted_seconds": s["distracted_seconds"],
        "report":             s["report"],
    }


@app.get("/focus/report")
def focus_report():
    report = fg.session_stats.get("report")
    if report is None:
        return JSONResponse({"available": False, "message": "No report yet"})
    return {"available": True, **report}


@app.get("/focus/stream")
def focus_stream():
    """MJPEG live feed — embed as <img src='http://localhost:8000/focus/stream'>"""
    import time as _time
    def generate():
        while fg.session_stats["active"]:
            frame = fg.session_stats.get("frame_bytes")
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            _time.sleep(0.05)
    return StreamingResponse(generate(),
                             media_type="multipart/x-mixed-replace; boundary=frame")