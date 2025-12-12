import sqlite3
from slack_sdk import WebClient
from post import post_upcoming, post_last_update, post_slack, post_changed
from backfill import backfill_missing_urls, check_status
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask 
from slackeventsapi import SlackEventAdapter
import os
import sys
from update import update
from excluded import irrelevant_hearings 


# ─── Setup SQLite ─────────────────────────────────────

conn = sqlite3.connect("hearings.db")
c    = conn.cursor() 
c.execute("""
CREATE TABLE IF NOT EXISTS hearings (
    id        TEXT PRIMARY KEY,
    date      TEXT,
    title     TEXT,
    committee TEXT,
    URL       TEXT,      
    API_call  TEXT,
    date_inserted TEXT,
    status    TEXT
)
""")
conn.commit()

# Set up Slack app
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app) 
client = WebClient(token=os.environ['SLACK_TOKEN']) 


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    # For server, check if the database path is set and the directory exists
    DB_PATH = os.getenv("DATABASE_PATH", "/app/data/hearings.db")
    if not Path("/app/data").is_dir():
        raise RuntimeError(
            "/app/data volume is not mounted – aborting."
        )
    
    # Create database if it doesn't exist
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) 
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hearings (
                id        TEXT PRIMARY KEY,
                date      TEXT,
                title     TEXT,
                committee TEXT,
                URL       TEXT,      
                API_call  TEXT,
                date_inserted TEXT,
                status    TEXT
            )
            """) 
    # "hearing_bot.py check_status" command checks for schedule changes
    if len(sys.argv) > 1 and sys.argv[1] == "check_status":
        check_status()

    # "hearing_bot.py update" command will run the update function
    elif len(sys.argv) > 1 and sys.argv[1] == "update":    
        print("Ran update function")
        daily_messages = update(DB_PATH) 

        if not daily_messages:
            print("No new hearings found.")           
            return
        for date_str, blocks in daily_messages.items():
            client.chat_postMessage(
                channel = "#hearings",
                text = f"New upcoming hearings on {date_str}",
                blocks=blocks
            )

    # "hearing_bot.py upcoming" command will post all upcoming hearings
    elif len(sys.argv) > 1 and sys.argv[1] == "upcoming":
        upcoming = post_upcoming()

        if upcoming:
            client.chat_postMessage(
                channel = "#private-test-channel",
                text = "New upcoming hearings:",
                blocks=upcoming
            )

    # "hearing_bot.py last_update" command will post the last posted hearings
    elif len(sys.argv) > 1 and sys.argv[1] == "last_update":
        last_update = post_last_update()

        if last_update:
            client.chat_postMessage(
            channel = "#private-test-channel",
            text = "Last posted hearings:",
            blocks=last_update
        )
            
    else:
        print("No command found")


if __name__ == '__main__':
    main()