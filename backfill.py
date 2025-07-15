from fetch import fetch_event_detail
from extract import get_URL, get_date, parse_date, get_status
import sqlite3 
from post import post_slack


def backfill_missing_urls():
    conn = sqlite3.connect("hearings.db")
    c    = conn.cursor()
    c.execute("""
        SELECT id, API_call
        FROM hearings
        WHERE (url IS NULL OR url = '')
          AND date(date) >= date('now')
    """)
    rows = c.fetchall()

    if not rows:
        print("No upcoming hearings' missing URLs to backfill.")
        c.close()
        return

    print(f"Backfilling URLs for {len(rows)} hearings…")

    for ev_id, api_call in rows:
        try:
            detail = fetch_event_detail(api_call)            # your existing detail fetcher
            url    = get_URL(detail)
            if not url:
                print(f"still no URL for {ev_id}, skipping")
                continue

            c.execute("""
                UPDATE hearings
                SET url          = ?,
                WHERE id = ?
            """, (url, ev_id))
            print(f"  • Filled URL for {ev_id}: {url}")
            conn.commit()
        except Exception as e:
            print(f"Error backfilling {ev_id}: {e}")
    c.close()
    print("Done backfilling.")

def check_status():
    # fetch all upcoming meetings 
    conn = sqlite3.connect("hearings.db")
    c    = conn.cursor()
    c.execute("""
        SELECT id, title, date, API_call, status
        FROM hearings
        WHERE date(date) >= date('now')
    """)
    rows = c.fetchall()
    if not rows:
        print("No upcoming hearings to check status.")
        conn.close()
        return
    
    # check if status has changed
    print(f"Checking status for {len(rows)} upcoming hearings…")
    for ev_id, title, date_str, api_call, status in rows:
        try:
            detail = fetch_event_detail(api_call)
            if not detail:
                print(f"No detail found for {title}, skipping")
                continue 

            new_status = get_status(detail)
            if new_status == status:
                # print(f"No status change for {title}")
                continue
            else:
                # status change:
                print(f"Status change for {title} on {date_str}: {status} → {new_status}")
                c.execute("""
                    UPDATE hearings
                    SET status = ?
                    WHERE id = ?
                """, (new_status, ev_id))
                conn.commit()

                try: 
                    # if status change, check if date has changed
                    new_date_obj = get_date(detail) 
                    new_dt = parse_date(new_date_obj)
                    new_date_str = new_dt.date().isoformat() 

                    # print (f"Checking date for {title}: {str_date} → {new_date_str}")
                    if date_str != new_date_str:
                        print(f"New date found for {title}: {new_date_str}") 
                        c.execute("""
                            UPDATE hearings
                            SET date = ?
                            WHERE id = ?
                        """, (new_date_str, ev_id))
                        conn.commit()
                    else: 
                        continue
                except Exception as e:
                    print(f"Error parsing date for {title}, skipping")
                    continue

        except Exception as e:
            print(f"Error updating date for {title}: {e}")

    # update_date()

    conn.close()
