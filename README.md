# 🗓️ AI Scheduler

Turn plain-English task descriptions into Google Calendar events — automatically finding free slots and handling conflicts.

---

## Project Structure

```
AI_SCHEDULER/
├── backend/
│   ├── main.py             # FastAPI app & all endpoints
│   ├── scheduler.py        # Free-slot finder & collision logic
│   ├── calendar_service.py # Google Calendar OAuth + event creation
│   ├── models.py           # Pydantic models
│   ├── credentials.json    # ← YOUR Google OAuth credentials (add this)
│   └── requirements.txt
├── frontend/
│   ├── app.py              # Streamlit UI
│   └── requirements.txt
└── .env                    # Environment variables
```

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Runtime |
| [Ollama](https://ollama.ai) | Local LLM for NL parsing |
| Google Cloud project | Calendar API access |

---

## Setup

### 1. Install Ollama & pull a model

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3        # or mistral, phi3, etc.
ollama serve              # starts on http://localhost:11434
```

### 2. Google Calendar credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Desktop app type)
4. Download `credentials.json` → place it in `backend/`
5. First run will open a browser for authorization; `token.pkl` is saved automatically

### 3. Configure `.env`

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
BACKEND_URL=http://localhost:8000
TIMEZONE=Asia/Kolkata
```

### 4. Install dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
pip install -r requirements.txt
```

### 5. Run

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Usage Examples

Type any of these into the scheduler input:

```
Study ML tomorrow at 5pm for 2 hours
Team standup every Monday at 9am for 30 minutes
Doctor appointment Friday at 2pm for 1 hour
Deep work session today at 10am for 3 hours
```

The app will:
1. Parse the task with Ollama (local LLM)
2. Check your Google Calendar for conflicts
3. Find the next free slot (shifts in 15-min increments if blocked)
4. Create the event and return a clickable Calendar link

---

## Focus Guardian

The **Focus Guardian** is a Pomodoro-style focus timer built into the sidebar:

- 25-minute sessions
- Tracks distraction warnings
- Auto-stops after the session ends
- Start/stop anytime from the UI

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/schedule` | Schedule a task from natural language |
| `POST` | `/focus/start` | Start a focus session |
| `POST` | `/focus/stop` | Stop the current session |
| `POST` | `/focus/distraction` | Report a distraction event |
| `GET`  | `/focus/status` | Get current focus session status |

### `POST /schedule` example

```json
// Request
{ "natural_language": "Study ML tomorrow at 5pm for 2 hours" }

// Response
{
  "success": true,
  "message": "Task scheduled successfully",
  "task": {
    "title": "Study ML",
    "start_time": "2025-06-11T17:00:00",
    "end_time": "2025-06-11T19:00:00",
    "calendar_event_link": "https://www.google.com/calendar/event?eid=...",
    "status": "scheduled",
    "note": null
  }
}
```

---

## Architecture

```
Streamlit (frontend)
    │  HTTP REST
    ▼
FastAPI (backend/main.py)
    ├── Ollama API  ──→  parse natural language → ParsedTask
    ├── scheduler.py ──→ resolve date/time, find free slot
    └── calendar_service.py ──→ Google Calendar OAuth, create event
```

---

## Customization

- **Change LLM**: Update `OLLAMA_MODEL` in `.env` (e.g. `mistral`, `phi3`, `gemma2`)
- **Timezone**: Update `TIMEZONE` in `.env` and `calendar_service.py`
- **Priority rules**: Edit `PRIORITY_KEYWORDS` dict in `scheduler.py`
- **Session length**: Change `FOCUS_DURATION` in `main.py` (default: 25 min)
