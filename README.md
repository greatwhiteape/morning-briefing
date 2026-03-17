# morning-briefing
DigitalOcean serverless function that delivers a daily morning briefing to Slack at 6am ET.
**What it sends:**
- Today's Google Calendar events
- Current weather for Bridgton, ME (Open-Meteo, no API key required)
## Prerequisites
- DigitalOcean account with Functions enabled
- Google Cloud service account with Calendar API access
- Slack Incoming Webhook
## Setup
See `.env.example` for required environment variables.
Deploy with:
```bash
doctl serverless deploy .
