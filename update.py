import sqlite3
from fetch import fetch_all, fetch_event_detail 
from extract import get_date, get_title, get_committee, get_URL, parse_date, get_status
from datetime import datetime, date
from post import post_slack 
from excluded import irrelevant_hearings 
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask 
from slackeventsapi import SlackEventAdapter
from slack_sdk import WebClient
import os
import sys # delete later

def delete_rows():
    """
    Deletes the last three inputted rows from the 'hearings.db' database,
    based on the 'date_inserted' column (assuming it stores insertion timestamps).
    """
    conn = sqlite3.connect('hearings.db')
    cursor = conn.cursor()

    # Fetch the primary key or ROWID of the last three inserted rows
    cursor.execute("""
        SELECT rowid FROM hearings
        ORDER BY date_inserted DESC
        LIMIT 7
    """)
    rows = cursor.fetchall()
    rowids_to_delete = [row[0] for row in rows]

    if rowids_to_delete:
        # Use a parameterized query to delete the rows
        cursor.execute(
            f"DELETE FROM hearings WHERE rowid IN ({','.join(['?']*len(rowids_to_delete))})",
            rowids_to_delete
        )
        conn.commit()

    conn.close()

def update():

    # Open SQLite DB
    conn = sqlite3.connect("hearings.db")
    c    = conn.cursor()

    # Preload seen IDs or start fresh if table missing
    try:
        c.execute("SELECT id FROM hearings")
        seen_ids = {row[0] for row in c.fetchall()}
    except Exception as e:
        seen_ids = set() 

    print(f"Seen IDs loaded: {len(seen_ids)}")

    known_errors = ["118388", "118320", "118290", "118290", "58326", "118259"] 
    new_hearings = [] 
    new_upcoming_hearings = []

    try:
        events = fetch_all("hearing") + fetch_all("meeting") 
        # events = fetch_all("hearing") 
    except Exception as e:
        print(f"Error fetching events: {e}")
        return

    for event in events:
        ev_id = event.get("eventId") or str(event.get("jacketNumber"))
        if ev_id in seen_ids or ev_id in known_errors: 
            continue
        seen_ids.add(ev_id)

        # Not in DB → fetch detail and parse date
        try:
            api_call = event["url"]
            detail    = fetch_event_detail(api_call)
            committee = get_committee(detail) 
            title     = get_title(detail)
            date_obj  = get_date(detail)
            url       = get_URL(detail)
            status    = get_status(detail)

        except Exception as e:
            print(f"Error processing event {ev_id}: {e}")
            continue 


        today = date.today().isoformat()

        try:
            dt = parse_date(date_obj)
            date_str = dt.date().isoformat()
            new_hearings.append((ev_id, date_str, title, committee, url, today, api_call, status))
            
            if date_str >= today:
                if committee in irrelevant_hearings:
                    print(f"Skipping irrelevant hearing titled {title} in {committee}")
                    continue 
                new_upcoming_hearings.append((date_str, committee, title, url)) 
                print(f"New hearing found: {status}: {date_str} | {committee} | {title}")
        
        except Exception as e:
            if ev_id in known_errors:
                # print(ev_id, "is known to have errors.")
                continue
            print(f"Error parsing {ev_id}: {e}")
            continue
 
    if not new_hearings:
        print("No new hearings found.")
        conn.close()
        return
    
    with conn:
        c.executemany(
            "INSERT INTO hearings (id, date, title, committee, url, date_inserted, API_call, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            new_hearings
        )
    conn.close()
    print(f"New upcoming hearings: {len(new_upcoming_hearings)}")
    if new_upcoming_hearings:
        return post_slack(new_upcoming_hearings) 


if __name__ == "__main__": 
    
    delete_rows()
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    app = Flask(__name__)
    slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app) 
    client = WebClient(token=os.environ['SLACK_TOKEN']) 

    daily_messages = update() 

    if not daily_messages:
        client.chat_postMessage(
            channel = "#private-test-channel",
            text = "No new upcoming hearings found."
        ) 
        sys.exit()
    
    print(daily_messages)
    for date_str, blocks in daily_messages.items():
        client.chat_postMessage(
            channel = "#private-test-channel",
            text = f"New upcoming hearings on {date_str}",
            blocks=blocks
        )