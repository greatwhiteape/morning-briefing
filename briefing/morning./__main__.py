import os
import json
import requests
from datetime import datetime
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
# ── CONFIG ──────────────────────────────────────────────────────────────
TIMEZONE = "America/New_York"
LOCATION_LAT = 44.0548
LOCATION_LON = -70.7148
LOCATION_LABEL = "Bridgton, ME"
CALENDAR_ID = "primary"
# ────────────────────────────────────────────────────────────────────────
def get_calendar_events(service_account_info):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
    )
    service = build("calendar", "v3", credentials=creds)
    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return result.get("items", [])
def get_weather():
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LOCATION_LAT}&longitude={LOCATION_LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
        f"&temperature_unit=fahrenheit&timezone={TIMEZONE}&forecast_days=1"
    )
    data = requests.get(url, timeout=10).json()
    daily = data["daily"]
    code = daily["weathercode"][0]
    high = round(daily["temperature_2m_max"][0])
    low = round(daily["temperature_2m_min"][0])
    return high, low, weather_code_to_text(code)
def weather_code_to_text(code):
    mapping = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 61: "Light rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Light snow", 73: "Moderate snow",
        75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 85: "Snow showers",
        95: "Thunderstorm", 99: "Thunderstorm with hail"
    }
    return mapping.get(code, f"Weather code {code}")
def format_event_time(event):
    start = event["start"].get("dateTime", event["start"].get("date"))
    end = event["end"].get("dateTime", event["end"].get("date"))
    if "" in start:
        tz = pytz.timezone(TIMEZONE)
        s = datetime.fromisoformat(start).astimezone(tz).strftime("%-I:%M %p")
        e = datetime.fromisoformat(end).astimezone(tz).strftime("%-I:%M %p")
        return f"{s} – {e}"
    return "All day"
def build_slack_message(events, high, low, weather_desc):
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).strftime("%A, %B %-d")
    if events:
        lines = []
        for e in events:
            title = e.get("summary", "(No title)")
            time_str = format_event_time(e)
            loc = e.get("location", "")
            loc_str = f"  —  {loc.split(',')[0]}" if loc else ""
            lines.append(f"- *{time_str}*  {title}{loc_str}")
        calendar_text = "\n".join(lines)
    else:
        calendar_text = "_No events scheduled today._"
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"☀️ Morning Briefing — {today}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*📅 Today's Calendar*\n{calendar_text}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*🌤️ Weather — {LOCATION_LABEL}*\n"
                        f"{weather_desc}   High: *{high}°F*  |  Low: *{low}°F*"
                    )
                }
            }
        ]
    }
def(args):
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not slack_webhook or not service_account_json:
        return {"error": "Missing required environment variables"}
    service_account_info = json.loads(service_account_json)
    try:
        events = get_calendar_events(service_account_info)
        high, low, weather_desc = get_weather()
        message = build_slack_message(events, high, low, weather_desc)
        resp = requests.post(slack_webhook, json=message, timeout=10)
        return {"status": resp.status_code, "events_count": len(events)}
    except Exception as e:
        return {"error": str(e)}
