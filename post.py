from fetch import fetch_event_detail
from extract import get_URL
import sqlite3
from html import escape 
from datetime import datetime
import time


# ─── Post upcoming meetings ─────────────────────────────────────────────────────
def post_upcoming():
    conn = sqlite3.connect("hearings.db")
    c = conn.cursor()
    c.execute("""
    SELECT
        date,
        committee,
        title, 
        url
    FROM hearings
    WHERE date(date) >= date('now') 
            AND strftime('%Y-%W', date) = strftime('%Y-%W', 'now')

    ORDER BY date(date) ASC;       
            
    """)
    rows = c.fetchall()
    if not rows:
        print("No upcoming hearings.")
    else:
        print(f"\nUpcoming hearings ({len(rows)}):")
        # print("Upcoming hearings:")
        return post_slack(rows)
        # for ev_id, ev_date, title, committee in rows:
        #     print(f"{ev_date} | {committee} | {title}")


# Post hearings that were last updated 
def post_last_update():
    conn = sqlite3.connect("hearings.db")
    c = conn.cursor()
    c.execute("SELECT MAX(date_inserted) FROM hearings WHERE date(date) >= date('now')")
    last_date = c.fetchone()[0] 
    print(last_date)
    if not last_date:
        print("No insertions found.")
        return

    print(f"\nLast posted hearings:")

    c.execute("""
        SELECT 
            date,
            committee,
            title,
            url
        FROM hearings
        WHERE date(date) >= date('now')
        AND date(date_inserted) = ?
        ORDER BY date(date) ASC
    """, (last_date,))

    rows = c.fetchall()
    if not rows:
        print("None found")
    else: 
        return post_slack(rows)

# Post hearings that were changed since last check
def post_changed():
    conn = sqlite3.connect("hearings.db")
    c = conn.cursor()
    c.execute("""
        SELECT 
            date,
            committee,
            title,
            url
        FROM hearings
        WHERE date(date) >= date('now')
        AND status != 'Scheduled'
        ORDER BY date(date) ASC
    """)
    rows = c.fetchall()
    if not rows:
        print("No changed hearings.")
        return

    print(f"\nChanged hearings ({len(rows)}):")
    post_slack(rows)

# Format date from "YYYY-MM-DD" to "Month Day, Year"
def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%B %-d, %Y")

# Structure hearings to post in Slack 
def post_slack(rows):
    """
    Given rows of (date_str, committee, title, url, status),
    prints them grouped by date in a bullet list.
    """
    
    # print(rows)
    by_date = {}

    for date_str, committee, title, url in rows:
        by_date[date_str] = by_date.get(date_str, [])
        by_date[date_str].append((committee, title, url))

    print(by_date)
    blocks: list[dict] = []
    daily_blocks: dict[str, list[dict]] = {}

    for date_str in sorted(by_date):
        blocks: list[dict] = []

        # date_formatted = format_date(date_str)  # e.g. returns f"<!date^{unix_timestamp}^{{date}}|{date_str}>"
        # 1) Date header (rich_text_section inside a rich_text block)
        # date_formatted = date_formatting(date_str) # e.g. returns f"<!date^{unix_timestamp}^{{date}}|{date_str}>"

        date_formatted = format_date(date_str)  # e.g. returns "June 1, 2024"
        blocks.append({
            "type": "rich_text",
            "elements": [{
                    "type": "rich_text_section",
                    "elements": [{ "type": "text", "text": date_formatted, "style": {"bold": True} }]
                }
            ]
        })

        # 2) Bulleted list for that date
        bullet_sections = []
        for committee, title, url in by_date[date_str]:
            # committee in **bold**
            section_elems = [
                {
                    "type": "text",
                    "text": f"{committee} | ",
                    "style": {"bold": True}
                }
            ]

            # linked or plain title
            if url is not None and url != "":
                section_elems.append({
                    "type": "link",
                    "url": url,
                    "text": title
                })
            else:
                section_elems.append({
                    "type": "text",
                    "text": title
                })

            bullet_sections.append({
                "type": "rich_text_section",
                "elements": section_elems
            })

        blocks.append({
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_list",
                    "style": "bullet",
                    "indent": 0,
                    "border": 0,
                    "elements": bullet_sections      # ≤ 50 items allowed per list :contentReference[oaicite:0]{index=0}
                }]
        })

        daily_blocks[date_str] = blocks

    return daily_blocks

        
if __name__ == "__main__":
    input = "06-01-2024"
    print(format_date(input))
