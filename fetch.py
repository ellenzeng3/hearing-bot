import requests
from datetime import date
from dotenv import load_dotenv
import os 
import sqlite3
from pathlib import Path
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from extract import get_URL


# ─── Configuration ────────────────────────────────────────────────────────────

CONGRESS = 119 # Update this for the current Congress session
HEARING_URL   = f"https://api.congress.gov/v3/hearing/{CONGRESS}"
MEETING_URL   = f"https://api.congress.gov/v3/committee-meeting/{CONGRESS}"
today = date.today().isoformat()  # e.g. "2025-06-18"

# Environment variables and session setup
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("CONGRESS_API_KEY")
HEADERS = {"X-Api-Key": API_KEY}

session = requests.Session()
session.headers.update({"X-Api-Key": API_KEY})
retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 502, 503, 504],
    allowed_methods=["GET"],
)

session.headers.update({"X-Api-Key": API_KEY})
session.mount("https://", HTTPAdapter(max_retries=retry))

# ─── Main fetches ───────────────────────────────────────────────────────────────

# Fetch all hearings or committee meetings for the current Congress
def fetch_all(kind):

    try:
        url = HEARING_URL if kind == "hearing" else MEETING_URL

        params = {
        "meetingStatus": "Scheduled",
        "limit": 250
        }

        r = session.get(url, params=params, timeout=10)
        r.raise_for_status() 
        key = "hearings" if kind == "hearing" else "committeeMeetings"
        return r.json().get(key, [])

    except Exception as e:
        print(f"Error fetching {kind}s: {e}")
        return []
    

# Fetch detailed information about a specific hearing or committee meeting
def fetch_event_detail(url):
     
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        r = session.get(url, headers=HEADERS, timeout=10) 
        r.raise_for_status()
        payload = r.json()
        return payload.get("hearing") or payload.get("committeeMeeting") or {}


    except Exception as e:
        print(f"Error fetching event detail: {e}")
        return {}
