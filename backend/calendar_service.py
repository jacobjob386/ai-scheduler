"""
calendar_service.py — Google Calendar OAuth + event creation.
Stores OAuth token in token.pkl for persistence.
"""

import os
import pickle
from datetime import datetime
from typing import List, Tuple, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pkl")


def get_calendar_service():
    """Authenticate and return a Google Calendar API service object."""
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("calendar", "v3", credentials=creds)


def get_existing_events(
    service, start: datetime, end: datetime
) -> List[Tuple[datetime, datetime, str]]:
    """Fetch events between start and end from Google Calendar."""
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    result = []
    for event in events:
        ev_start = event["start"].get("dateTime", event["start"].get("date"))
        ev_end = event["end"].get("dateTime", event["end"].get("date"))
        title = event.get("summary", "Untitled")
        try:
            result.append((
                datetime.fromisoformat(ev_start.replace("Z", "")),
                datetime.fromisoformat(ev_end.replace("Z", "")),
                title,
            ))
        except Exception:
            continue
    return result


def create_calendar_event(
    service,
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
) -> Optional[str]:
    """Create a Google Calendar event and return the HTML link."""
    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Kolkata"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 10}],
        },
    }
    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return event.get("htmlLink")