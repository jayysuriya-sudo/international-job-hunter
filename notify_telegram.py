import json
import os
import urllib.parse
import urllib.request


# ==================================================
# FILE
# ==================================================

JOBS_FILE = "jobs.json"


# ==================================================
# TELEGRAM
# ==================================================

BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN"
)

CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID"
)


# ==================================================
# LOAD JOBS
# ==================================================

def load_jobs():

    try:

        with open(
            JOBS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data.get(
            "jobs",
            []
        )

    except Exception as error:

        print(
            f"❌ Could not load jobs.json: {error}"
        )

        return []


# ==================================================
# TELEGRAM MESSAGE
# ==================================================

def format_job(
    job,
    number
):

    title = job.get(
        "title",
        "Unknown position"
    )

    company = job.get(
        "company",
        "Unknown company"
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

    rating = job.get(
        "rating",
        ""
    )

    visa = job.get(
        "visa_status",
        "❓ Not confirmed"
    )

    relocation = job.get(
        "relocation_status",
        "❓ Not mentioned"
    )

    experience = job.get(
        "experience_required",
        "Not specified"
    )

    source = job.get(
        "source",
        "Unknown"
    )

    url = job.get(
        "url",
        ""
    )

    reasons = job.get(
        "match_reasons",
        []
    )

    # ------------------------------------------
    # MATCH REASONS
    # ------------------------------------------

    if reasons:

        reason_text = "\n".join(
            f"✓ {reason}"
            for reason in reasons
        )

    else:

        reason_text = (
            "✓ Relevant creative opportunity"
        )

    # ------------------------------------------
    # MESSAGE
    # ------------------------------------------

    message = (
        f"🎯 <b>JOB #{number}</b>\n\n"

        f"💼 <b>{escape_html(title)}</b>\n"
        f"🏢 {escape_html(company)}\n"
        f"📍 {escape_html(location)}\n\n"

        f"💰 <b>Salary:</b> "
        f"{escape_html(str(salary))}\n"

        f"⭐ <b>Match Score:</b> "
        f"{score}/100 "
        f"{rating}\n\n"

        f"🎯 <b>WHY IT MATCHES</b>\n"
        f"{reason_text}\n\n"

        f"🧑‍💼 <b>Experience:</b> "
        f"{escape_html(str(experience))}\n\n"

        f"🛂 <b>Visa Sponsorship:</b> "
        f"{escape_html(str(visa))}\n"

        f"✈️ <b>Relocation:</b> "
        f"{escape_html(str(relocation))}\n\n"

        f"🔎 <b>Source:</b> "
        f"{escape_html(source)}\n\n"

        f"🔗 <b>APPLY:</b>\n"
        f"{url}\n\n"

        f"👉 Review this job before applying."
    )

    return message


# ==================================================
# HTML ESCAPE
# ==================================================

def escape_html(text):

    text = str(text)

    text = text.replace(
        "&",
        "&amp;"
    )

    text = text.replace(
        "<",
        "&lt;"
    )

    text = text.replace(
        ">",
        "&gt;"
    )

    return text


# ==================================================
# SEND TELEGRAM
# ==================================================

def send_telegram(
    message
):

    if not BOT_TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN is missing"
        )

        return False

    if not CHAT_ID:

        print(
            "❌ TELEGRAM_CHAT_ID is missing"
        )

        return False

    api_url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true"
    }).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        api_url,
        data=data,
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if result.get(
            "ok"
        ):

            return True

        print(
            f"❌ Telegram error: {result}"
        )

        return False

    except Exception as error:

        print(
            f"❌ Telegram request failed: {error}"
        )

        return False


# ==================================================
# MAIN
# ==================================================

def main():

    print(
        "=========================================="
    )

    print(
        "📱 TELEGRAM JOB NOTIFIER 5.0"
    )

    print(
        "=========================================="
    )

    jobs = load_jobs()

    if not jobs:

        print(
            "⚠️ No jobs to send."
        )

        return

    print(
        f"📨 Sending {len(jobs)} jobs..."
    )

    sent = 0

    for number, job in enumerate(
        jobs,
        1
    ):

        message = format_job(
            job,
            number
        )

        success = send_telegram(
            message
        )

        if success:

            sent += 1

            print(
                f"✅ Job #{number} sent"
            )

        else:

            print(
                f"❌ Job #{number} failed"
            )

    print("")
    print(
        f"📨 SENT: {sent}/{len(jobs)}"
    )

    print(
        "✅ TELEGRAM NOTIFICATION COMPLETE"
    )


if __name__ == "__main__":

    main()
