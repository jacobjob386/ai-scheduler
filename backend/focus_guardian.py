"""
focus_guardian.py — Webcam-based distraction detection using MediaPipe.

Runs in a background thread during a focus session.
Tracks:
  - Face absence (user left)
  - Head pose deviation (looking away)
  - Eyes closed duration (drowsiness)

Writes real-time stats into a shared `session_stats` dict
that the FastAPI endpoints read from.
"""

import time
import threading
import math
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

# ── MediaPipe setup ──────────────────────────────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh

# Landmark indices for eye openness (EAR — Eye Aspect Ratio)
# Left eye: 33, 160, 158, 133, 153, 144
# Right eye: 362, 385, 387, 263, 373, 380
LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Nose tip and chin for rough head-pose yaw check
NOSE_TIP   = 1
LEFT_CHEEK = 234
RIGHT_CHEEK = 454

EAR_THRESHOLD      = 0.22   # below this = eyes closed
DROWSY_SECONDS     = 2.5    # eyes closed longer than this → drowsy event
YAW_THRESHOLD      = 25     # degrees away from centre → looking away
ABSENT_THRESHOLD   = 3.0    # seconds without face → absent event
FOCUS_DURATION_SEC = 25 * 60


# ── Shared state (written by guardian thread, read by FastAPI) ───────────────
session_stats: dict = {
    "active":              False,
    "start_time":          None,
    "elapsed_seconds":     0,
    "remaining_seconds":   FOCUS_DURATION_SEC,

    # Distraction counters
    "absent_events":       0,   # face disappeared
    "look_away_events":    0,   # head turned too far
    "drowsy_events":       0,   # eyes closed too long

    # Cumulative distracted time (seconds)
    "distracted_seconds":  0,

    # Focus score 0-100
    "focus_score":         100,

    # Live frame (JPEG bytes) for streaming to UI
    "frame_bytes":         None,

    # End-of-session report
    "report":              None,
}

_stop_event  = threading.Event()
_guard_thread: Optional[threading.Thread] = None


# ── Geometry helpers ─────────────────────────────────────────────────────────

def _dist(a, b) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _ear(landmarks, eye_indices) -> float:
    """Eye Aspect Ratio — lower value means more closed."""
    p = [landmarks[i] for i in eye_indices]
    # Vertical distances
    v1 = _dist(p[1], p[5])
    v2 = _dist(p[2], p[4])
    # Horizontal distance
    h  = _dist(p[0], p[3])
    return (v1 + v2) / (2.0 * h + 1e-6)


def _yaw_degrees(landmarks, img_w, img_h) -> float:
    """Estimate horizontal head rotation from nose vs cheek x-positions."""
    nose  = landmarks[NOSE_TIP]
    left  = landmarks[LEFT_CHEEK]
    right = landmarks[RIGHT_CHEEK]

    mid_x = (left.x + right.x) / 2.0
    # Positive yaw = turned right, negative = turned left
    yaw = (nose.x - mid_x) * 180
    return yaw


# ── Main guardian loop ───────────────────────────────────────────────────────

def _run_guardian():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        session_stats["report"] = _build_report(error="Could not open webcam.")
        session_stats["active"] = False
        return

    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    start_time      = session_stats["start_time"]
    last_face_time  = time.time()
    eye_close_start: Optional[float] = None
    distracted_start: Optional[float] = None   # when current distraction began

    total_distracted = 0.0

    while not _stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        now     = time.time()
        elapsed = now - start_time

        # Auto-stop after 25 minutes
        if elapsed >= FOCUS_DURATION_SEC:
            break

        session_stats["elapsed_seconds"]   = int(elapsed)
        session_stats["remaining_seconds"] = max(0, FOCUS_DURATION_SEC - int(elapsed))

        h, w = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        distracted_now = False

        if result.multi_face_landmarks:
            lms = result.multi_face_landmarks[0].landmark
            last_face_time = now

            # ── Eye Aspect Ratio ────────────────────────────────────────────
            ear = (_ear(lms, LEFT_EYE) + _ear(lms, RIGHT_EYE)) / 2.0

            if ear < EAR_THRESHOLD:
                if eye_close_start is None:
                    eye_close_start = now
                elif now - eye_close_start > DROWSY_SECONDS:
                    session_stats["drowsy_events"] += 1
                    eye_close_start = now   # reset to avoid double-counting
                    distracted_now = True
            else:
                eye_close_start = None

            # ── Head pose (yaw) ─────────────────────────────────────────────
            yaw = _yaw_degrees(lms, w, h)
            if abs(yaw) > YAW_THRESHOLD:
                session_stats["look_away_events"] += 1
                distracted_now = True

            # ── Draw overlay ────────────────────────────────────────────────
            color = (0, 255, 120) if not distracted_now else (0, 80, 255)
            cv2.putText(frame, f"EAR: {ear:.2f}  Yaw: {yaw:.1f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        else:
            # No face detected
            absent = now - last_face_time
            if absent > ABSENT_THRESHOLD:
                session_stats["absent_events"] += 1
                last_face_time = now   # reset
                distracted_now = True

            cv2.putText(frame, "No face detected",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 80, 255), 2)

        # ── Accumulate distracted time ───────────────────────────────────────
        if distracted_now:
            if distracted_start is None:
                distracted_start = now
        else:
            if distracted_start is not None:
                total_distracted += now - distracted_start
                distracted_start = None

        session_stats["distracted_seconds"] = int(total_distracted)

        # ── Focus score ──────────────────────────────────────────────────────
        if elapsed > 0:
            ratio = total_distracted / elapsed
            session_stats["focus_score"] = max(0, int(100 - ratio * 100))

        # ── Status overlay ───────────────────────────────────────────────────
        remaining_min = (FOCUS_DURATION_SEC - int(elapsed)) // 60
        remaining_sec = (FOCUS_DURATION_SEC - int(elapsed)) % 60
        cv2.putText(frame, f"{remaining_min:02d}:{remaining_sec:02d} left",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 255), 2)

        label = "FOCUSED" if not distracted_now else "DISTRACTED"
        lcolor = (0, 220, 80) if not distracted_now else (0, 60, 220)
        cv2.putText(frame, label, (w - 160, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, lcolor, 2)

        # ── Encode frame for streaming ───────────────────────────────────────
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        session_stats["frame_bytes"] = buf.tobytes()

        time.sleep(0.05)   # ~20 fps

    # Flush any trailing distracted window
    if distracted_start is not None:
        total_distracted += time.time() - distracted_start

    cap.release()
    face_mesh.close()

    session_stats["active"]             = False
    session_stats["distracted_seconds"] = int(total_distracted)
    session_stats["report"]             = _build_report()


def _build_report(error: str = None) -> dict:
    """Build the end-of-session summary dict."""
    stats = session_stats
    elapsed = stats["elapsed_seconds"] or 1
    distracted = stats["distracted_seconds"]
    focused    = max(0, elapsed - distracted)
    score      = stats["focus_score"]

    if error:
        return {"error": error}

    # Grade
    if score >= 85:
        grade, emoji = "Excellent", "🏆"
    elif score >= 70:
        grade, emoji = "Good", "✅"
    elif score >= 50:
        grade, emoji = "Fair", "⚠️"
    else:
        grade, emoji = "Poor", "❌"

    return {
        "duration_seconds":   elapsed,
        "focused_seconds":    focused,
        "distracted_seconds": distracted,
        "absent_events":      stats["absent_events"],
        "look_away_events":   stats["look_away_events"],
        "drowsy_events":      stats["drowsy_events"],
        "focus_score":        score,
        "grade":              grade,
        "grade_emoji":        emoji,
        "tip": _tip(score, stats),
    }


def _tip(score: int, stats: dict) -> str:
    """Return a personalised improvement tip."""
    if stats["absent_events"] > stats["look_away_events"]:
        return "You left your desk frequently. Try the 'no-leave' rule during Pomodoros."
    if stats["drowsy_events"] > 2:
        return "Drowsiness detected often. Get a good night's sleep before your next session."
    if stats["look_away_events"] > 5:
        return "You looked away often. Keep your study material directly in front of you."
    if score >= 85:
        return "Outstanding focus! Keep up the consistency."
    return "Reduce distractions — phone away, notifications off."


# ── Public API ───────────────────────────────────────────────────────────────

def start_session():
    global _guard_thread
    _stop_event.clear()
    session_stats.update({
        "active":             True,
        "start_time":         time.time(),
        "elapsed_seconds":    0,
        "remaining_seconds":  FOCUS_DURATION_SEC,
        "absent_events":      0,
        "look_away_events":   0,
        "drowsy_events":      0,
        "distracted_seconds": 0,
        "focus_score":        100,
        "frame_bytes":        None,
        "report":             None,
    })
    _guard_thread = threading.Thread(target=_run_guardian, daemon=True)
    _guard_thread.start()


def stop_session():
    _stop_event.set()
    session_stats["active"] = False