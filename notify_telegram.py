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
        "disable_web_page_preview": "false"
    }).encode()

    request = urllib.request.Request(
        url,
        data=data
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return response.read().decode()


with open(
    "jobs.json",
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


jobs = data.get("jobs", [])


if not jobs:

    send_message(
        "🔎 INTERNATIONAL JOB HUNTER\n\n"
        "No strong international matches found today.\n\n"
        "🌍 I'll keep searching for better opportunities."
    )

else:

    send_message(
        "🚀 INTERNATIONAL JOB HUNTER\n\n"
        f"⭐ {len(jobs)} strong matches found today.\n\n"
        "Priority: High-paying international creative jobs"
    )

    for number, job in enumerate(
        jobs,
        1
    ):

        title = job.get(
            "title",
            "Unknown"
        )

        company = job.get(
            "company",
            "Unknown"
        )

        location = job.get(
            "location",
            "Not specified"
        )

        salary = job.get(
            "salary",
            "Not listed"
        )

        score = job.get(
            "score",
            0
        )

        source = job.get(
            "source",
            "Unknown"
        )

        url = job.get(
            "url",
            ""
        )

        description = job.get(
            "description",
            ""
        ).lower()

        # Visa / relocation detection
        visa = "❓ Not mentioned"

        if (
            "visa sponsorship" in description
            or "visa sponsor" in description
            or "work visa" in description
            or "sponsorship available" in description
        ):
            visa = "🛂 Visa sponsorship mentioned"

        relocation = "❓ Not mentioned"

        if (
            "relocation" in description
            or "relocation package" in description
            or "relocation assistance" in description
        ):
            relocation = "✈️ Relocation mentioned"

        message = (
            f"🎯 JOB #{number}\n\n"
            f"💼 {title}\n"
            f"🏢 {company}\n"
            f"📍 {location}\n"
            f"💰 Salary: {salary}\n"
            f"⭐ Match Score: {score}/100+\n"
            f"🛂 {visa}\n"
            f"{relocation}\n"
            f"🔎 Source: {source}\n\n"
            f"🔗 APPLY:\n{url}\n\n"
            f"👉 Review this job before applying."
        )

        send_message(message)
