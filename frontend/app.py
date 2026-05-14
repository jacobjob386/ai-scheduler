"""
app.py — AI Scheduler Streamlit Frontend (v2 — webcam Focus Guardian)
Run with: streamlit run app.py
"""

import os
import time
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Scheduler", page_icon="🗓️",
                   layout="centered", initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0f;
    color: #e8e6f0;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2.5rem 2rem 4rem; max-width: 780px; }

.hero-title {
    font-family: 'Syne', sans-serif; font-weight: 800; font-size: 3rem;
    background: linear-gradient(135deg,#c084fc,#818cf8,#38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.2rem;
}
.hero-sub { font-size: 1rem; color: #7c7a8e; margin-bottom: 2rem; }

.stTextArea textarea {
    background:#13121c!important; border:1.5px solid #2e2c3f!important;
    border-radius:14px!important; color:#e8e6f0!important;
    font-family:'DM Sans',sans-serif!important; font-size:1rem!important;
    padding:1rem!important; resize:none!important;
}
.stTextArea textarea:focus {
    border-color:#818cf8!important;
    box-shadow:0 0 0 3px rgba(129,140,248,0.15)!important;
}
.stButton>button {
    width:100%; background:linear-gradient(135deg,#7c3aed,#4f46e5)!important;
    color:white!important; border:none!important; border-radius:12px!important;
    padding:0.75rem 1.5rem!important; font-family:'Syne',sans-serif!important;
    font-weight:600!important; font-size:1rem!important; transition:all .2s!important;
}
.stButton>button:hover { transform:translateY(-2px)!important; box-shadow:0 8px 24px rgba(124,58,237,.4)!important; }

.result-card {
    background:linear-gradient(145deg,#13121c,#1a1828);
    border:1px solid #2e2c3f; border-radius:18px;
    padding:1.6rem 1.8rem; margin-top:1.5rem;
    box-shadow:0 4px 32px rgba(0,0,0,.4);
}
.result-card .task-title { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:700; color:#c4b5fd; margin-bottom:.8rem; }
.time-row { display:flex; gap:1rem; margin-bottom:.8rem; }
.time-chip { background:#1e1c2e; border:1px solid #3730a3; border-radius:8px; padding:.4rem .9rem; font-size:.9rem; color:#a5b4fc; flex:1; text-align:center; }
.time-chip span { display:block; font-size:.72rem; color:#6b6880; margin-bottom:2px; }
.status-badge { display:inline-block; padding:.25rem .8rem; border-radius:99px; font-size:.78rem; font-weight:500; letter-spacing:.04em; margin-bottom:.8rem; }
.status-scheduled { background:#052e16; color:#4ade80; border:1px solid #166534; }
.status-shifted    { background:#431407; color:#fb923c; border:1px solid #9a3412; }
.note-text { font-size:.85rem; color:#7c7a8e; margin-top:.5rem; }
.cal-btn { display:inline-flex; align-items:center; gap:.5rem; margin-top:1rem; padding:.6rem 1.2rem; background:linear-gradient(135deg,#0f766e,#0284c7); border-radius:10px; color:white!important; text-decoration:none!important; font-family:'Syne',sans-serif; font-size:.9rem; font-weight:600; }

.divider { border:none; border-top:1px solid #1e1c2e; margin:2rem 0; }

/* Focus Guardian */
.focus-card { background:linear-gradient(145deg,#0f0c1a,#160f2a); border:1px solid #3b1d6e; border-radius:18px; padding:1.6rem 1.8rem; margin-top:1rem; }
.focus-title { font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:700; color:#e879f9; margin-bottom:.3rem; }
.focus-desc { font-size:.88rem; color:#7c7a8e; margin-bottom:1.2rem; }

/* Live stats grid */
.stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:1rem 0; }
.stat-box { background:#120d22; border:1px solid #2d1b5e; border-radius:10px; padding:.7rem; text-align:center; }
.stat-num { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; }
.stat-lbl { font-size:.72rem; color:#7c7a8e; margin-top:2px; }
.focused-num   { color:#4ade80; }
.away-num      { color:#f59e0b; }
.absent-num    { color:#f87171; }
.drowsy-num    { color:#818cf8; }
.score-big     { font-family:'Syne',sans-serif; font-size:3.5rem; font-weight:800; }

/* Report card */
.report-card { background:linear-gradient(145deg,#0d1a0d,#0a1520); border:1px solid #1a3d1a; border-radius:18px; padding:1.6rem 1.8rem; margin-top:1.2rem; }
.report-title { font-family:'Syne',sans-serif; font-size:1.2rem; font-weight:700; color:#86efac; margin-bottom:1rem; }
.report-row { display:flex; justify-content:space-between; padding:.5rem 0; border-bottom:1px solid #1a2a1a; font-size:.9rem; }
.report-row:last-child { border-bottom:none; }
.tip-box { background:#0c1c0c; border:1px solid #166534; border-radius:10px; padding:.8rem 1rem; margin-top:.8rem; font-size:.88rem; color:#86efac; }

.err-box  { background:#1a0505; border:1px solid #7f1d1d; border-radius:12px; padding:1rem 1.2rem; color:#f87171; font-size:.9rem; margin-top:1rem; }
.info-box { background:#0c1a2e; border:1px solid #1e3a5f; border-radius:12px; padding:.9rem 1.2rem; color:#7dd3fc; font-size:.85rem; margin-top:.8rem; }
.history-item { background:#0f0e17; border:1px solid #1e1c2e; border-radius:12px; padding:.9rem 1.2rem; margin-bottom:.6rem; display:flex; justify-content:space-between; align-items:center; }
.history-title { font-weight:500; color:#c4b5fd; font-size:.95rem; }
.history-time  { font-size:.8rem; color:#6b6880; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("history", []), ("last_result", None), ("show_report", False)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ───────────────────────────────────────────────────────────────────
def api(path, method="GET", payload=None):
    url = f"{BACKEND_URL}{path}"
    try:
        r = (requests.post(url, json=payload, timeout=60) if method == "POST"
             else requests.get(url, timeout=10))
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the backend. Is uvicorn running on port 8000?"
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except requests.exceptions.HTTPError as e:
        detail = ""
        try: detail = e.response.json().get("detail","")
        except Exception: pass
        return None, f"Backend error {e.response.status_code}: {detail}"
    except Exception as e:
        return None, str(e)


def fmt_time(iso_str):
    try: return datetime.fromisoformat(iso_str).strftime("%a, %b %d · %I:%M %p")
    except Exception: return iso_str


def score_color(score):
    if score >= 85: return "#4ade80"
    if score >= 70: return "#a3e635"
    if score >= 50: return "#f59e0b"
    return "#f87171"


def fmt_seconds(s):
    m, sec = divmod(s, 60)
    return f"{m}m {sec}s"


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">AI Scheduler</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Turn plain English into calendar events — instantly.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════
task_input = st.text_area(
    label="Task", label_visibility="collapsed", height=100,
    placeholder='"Study ML tomorrow at 5pm for 2 hours"  •  "Team standup Monday 9am for 30 minutes"',
)

col1, col2 = st.columns([3, 1])
with col1: schedule_btn = st.button("⚡ Schedule Task", use_container_width=True)
with col2: clear_btn    = st.button("Clear",           use_container_width=True)

if clear_btn:
    st.session_state.last_result = None
    st.rerun()

if schedule_btn and task_input.strip():
    with st.spinner("🤖 Parsing with Ollama & finding a free slot…"):
        data, err = api("/schedule", "POST", {"natural_language": task_input.strip()})
    if err:
        st.markdown(f'<div class="err-box">❌ {err}</div>', unsafe_allow_html=True)
    elif data and data.get("success"):
        st.session_state.last_result = data["task"]
        st.session_state.history.insert(0, data["task"])
        if len(st.session_state.history) > 10:
            st.session_state.history.pop()
    else:
        st.markdown(f'<div class="err-box">⚠️ {(data or {}).get("message","Unknown error")}</div>', unsafe_allow_html=True)
elif schedule_btn:
    st.markdown('<div class="info-box">✏️ Please type a task description first.</div>', unsafe_allow_html=True)

# Result card
if st.session_state.last_result:
    t = st.session_state.last_result
    cls   = "status-shifted" if t.get("status") == "shifted" else "status-scheduled"
    label = "⚠️ Shifted" if t.get("status") == "shifted" else "✅ Scheduled"
    cal   = f'<a href="{t["calendar_event_link"]}" target="_blank" class="cal-btn">📅 Open in Google Calendar</a>' if t.get("calendar_event_link") else ""
    note  = f'<div class="note-text">ℹ️ {t["note"]}</div>' if t.get("note") else ""
    st.markdown(f"""
    <div class="result-card">
        <div class="task-title">📌 {t['title']}</div>
        <span class="status-badge {cls}">{label}</span>
        <div class="time-row">
            <div class="time-chip"><span>START</span>{fmt_time(t['start_time'])}</div>
            <div class="time-chip"><span>END</span>{fmt_time(t['end_time'])}</div>
        </div>
        {note}{cal}
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOCUS GUARDIAN
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="focus-card">
    <div class="focus-title">🛡️ Focus Guardian</div>
    <div class="focus-desc">Webcam-powered distraction detection · 25-min Pomodoro · generates a focus report when done</div>
""", unsafe_allow_html=True)

status, serr = api("/focus/status")

if serr:
    st.markdown(f'<div class="err-box">❌ {serr}</div>', unsafe_allow_html=True)
elif status and status.get("active"):
    # ── LIVE SESSION ──────────────────────────────────────────────────────────
    elapsed   = status["elapsed_seconds"]
    remaining = status["remaining_seconds"]
    score     = status["focus_score"]
    mins_left = remaining // 60
    secs_left = remaining % 60

    st.progress(min(elapsed / (25 * 60), 1.0),
                text=f"⏱️ {mins_left:02d}:{secs_left:02d} remaining")

    # Live webcam feed via MJPEG img tag
    st.markdown(
        f'<img src="{BACKEND_URL}/focus/stream" '
        f'style="width:100%;border-radius:12px;border:1px solid #2d1b5e;margin:0.5rem 0;" '
        f'alt="Live webcam feed"/>',
        unsafe_allow_html=True,
    )

    # Live stats
    sc_color = score_color(score)
    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-num" style="color:{sc_color};">{score}</div>
            <div class="stat-lbl">Focus Score</div>
        </div>
        <div class="stat-box">
            <div class="stat-num away-num">{status['look_away_events']}</div>
            <div class="stat-lbl">Looked Away</div>
        </div>
        <div class="stat-box">
            <div class="stat-num absent-num">{status['absent_events']}</div>
            <div class="stat-lbl">Left Desk</div>
        </div>
        <div class="stat-box">
            <div class="stat-num drowsy-num">{status['drowsy_events']}</div>
            <div class="stat-lbl">Drowsy Events</div>
        </div>
        <div class="stat-box">
            <div class="stat-num focused-num">{fmt_seconds(max(0, elapsed - status['distracted_seconds']))}</div>
            <div class="stat-lbl">Focused Time</div>
        </div>
        <div class="stat-box">
            <div class="stat-num" style="color:#f87171;">{fmt_seconds(status['distracted_seconds'])}</div>
            <div class="stat-lbl">Distracted Time</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if st.button("⛔ Stop & Get Report", use_container_width=True):
        api("/focus/stop", "POST")
        st.session_state.show_report = True
        st.rerun()

    # Auto-refresh every 2 seconds
    time.sleep(2)
    st.rerun()

else:
    # ── IDLE — show start button or report ───────────────────────────────────
    report_data, _ = api("/focus/report")
    has_report = report_data and report_data.get("available")

    if has_report and (st.session_state.show_report or True):
        r = report_data
        sc = r["focus_score"]
        sc_c = score_color(sc)
        st.markdown(f"""
        <div class="report-card">
            <div class="report-title">{r['grade_emoji']} Session Report — {r['grade']}</div>
            <div style="text-align:center;margin-bottom:1rem;">
                <span class="score-big" style="color:{sc_c};">{sc}</span>
                <div style="font-size:.8rem;color:#7c7a8e;">Focus Score</div>
            </div>
            <div class="report-row"><span>Total Duration</span><span>{fmt_seconds(r['duration_seconds'])}</span></div>
            <div class="report-row"><span>✅ Focused Time</span><span style="color:#4ade80;">{fmt_seconds(r['focused_seconds'])}</span></div>
            <div class="report-row"><span>😵 Distracted Time</span><span style="color:#f87171;">{fmt_seconds(r['distracted_seconds'])}</span></div>
            <div class="report-row"><span>👀 Looked Away</span><span style="color:#f59e0b;">{r['look_away_events']} times</span></div>
            <div class="report-row"><span>🚶 Left Desk</span><span style="color:#f87171;">{r['absent_events']} times</span></div>
            <div class="report-row"><span>😴 Drowsy Events</span><span style="color:#818cf8;">{r['drowsy_events']} times</span></div>
            <div class="tip-box">💡 {r['tip']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <ul style="color:#6b6880;font-size:.85rem;padding-left:1.2rem;margin:.8rem 0 1rem;">
        <li>Webcam monitors your face the entire session</li>
        <li>Detects: looking away · leaving desk · drowsiness</li>
        <li>Generates a detailed focus report at the end</li>
        <li>Grant camera permission when the browser asks</li>
    </ul>""", unsafe_allow_html=True)

    if st.button("🎯 Start Focus Session", use_container_width=True):
        result, err = api("/focus/start", "POST")
        if err:
            st.markdown(f'<div class="err-box">❌ {err}</div>', unsafe_allow_html=True)
        else:
            st.session_state.show_report = False
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.history:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:1.1rem;color:#c4b5fd;margin-bottom:.8rem;">Recent Tasks</div>', unsafe_allow_html=True)
    for item in st.session_state.history[:5]:
        start_fmt = fmt_time(item["start_time"])
        end_fmt   = datetime.fromisoformat(item["end_time"]).strftime("%I:%M %p")
        badge     = "↗ shifted" if item.get("status") == "shifted" else "✓"
        st.markdown(f"""
        <div class="history-item">
            <div>
                <div class="history-title">{item['title']}</div>
                <div class="history-time">{start_fmt} → {end_fmt}</div>
            </div>
            <div style="font-size:.75rem;color:#4ade80;">{badge}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('<div style="text-align:center;color:#2e2c3f;font-size:.75rem;margin-top:3rem;">AI Scheduler · Webcam Focus Guardian · Ollama + Google Calendar</div>', unsafe_allow_html=True)