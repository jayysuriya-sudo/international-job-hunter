import json
import os
import urllib.parse
import urllib.request

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": "true"
    }).encode()

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode()


with open("jobs.json", "r", encoding="utf-8") as f:
    data = json.load(f)

jobs = data.get("jobs", [])

if not jobs:
    send_message(
        "🔎 International Job Hunter\n\n"
        "No strong matching jobs found today.\n"
        "I'll keep searching."
    )
else:
    send_message(
        f"🚀 INTERNATIONAL JOB HUNTER\n\n"
        f"Found {len(jobs)} strong job matches today."
    )

    for i, job in enumerate(jobs, 1):
        message = (
            f"🎯 JOB #{i}\n\n"
            f"💼 {job['title']}\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"⭐ Match Score: {job['score']}\n"
            f"🔎 Source: {job['source']}\n\n"
            f"🔗 {job['url']}"
        )

        send_message(message)
