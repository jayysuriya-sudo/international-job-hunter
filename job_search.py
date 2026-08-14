import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

CONFIG_FILE = "config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_json(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "InternationalJobHunter/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Source error: {e}")
        return None


def fetch_arbeitnow():
    data = get_json("https://www.arbeitnow.com/api/job-board-api")
    if not data:
        return []

    jobs = []

    for job in data.get("data", []):
        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "source": "Arbeitnow"
        })

    return jobs


def fetch_remotive():
    data = get_json("https://remotive.com/api/remote-jobs")
    if not data:
        return []

    jobs = []

    for job in data.get("jobs", []):
        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("candidate_required_location", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "source": "Remotive"
        })

    return jobs


def matches_title(job, config):
    text = job["title"].lower()

    for title in config["job_titles"]:
        if title.lower() in text:
            return True

    return False


def is_excluded(job, config):
    text = (
        job["location"] + " " +
        job["title"] + " " +
        job["description"]
    ).lower()

    for location in config["exclude_locations"]:
        if location.lower() in text:
            return True

    return False


def score_job(job, config):
    text = (
        job["title"] + " " +
        job["location"] + " " +
        job["description"]
    ).lower()

    score = 0

    # Job-title relevance
    for title in config["job_titles"]:
        if title.lower() in job["title"].lower():
            score += 25

    # International opportunities
    international_keywords = [
        "visa sponsorship",
        "visa sponsor",
        "relocation",
        "relocation package",
        "work permit",
        "sponsorship",
        "international"
    ]

    for keyword in international_keywords:
        if keyword in text:
            score += 12

    # High-value creative industries
    priority_keywords = [
        "film",
        "media",
        "advertising",
        "production",
        "creative",
        "entertainment",
        "technology",
        "content",
        "brand"
    ]

    for keyword in priority_keywords:
        if keyword in text:
            score += 4

    # Seniority
    senior_keywords = [
        "senior",
        "lead",
        "head",
        "manager",
        "producer"
    ]

    for keyword in senior_keywords:
        if keyword in job["title"].lower():
            score += 8

    # Remote
    if "remote" in text:
        score += 10

    return score


def main():
    config = load_config()

    print("🔎 Searching international jobs...")

    jobs = []

    jobs.extend(fetch_arbeitnow())
    jobs.extend(fetch_remotive())

    print(f"Found {len(jobs)} total jobs.")

    filtered = []

    for job in jobs:

        if not matches_title(job, config):
            continue

        if is_excluded(job, config):
            continue

        job["score"] = score_job(job, config)

        filtered.append(job)

    # Remove duplicates
    unique = {}

    for job in filtered:
        key = job["url"]

        if key and key not in unique:
            unique[key] = job

    filtered = list(unique.values())

    # Highest scoring first
    filtered.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    filtered = filtered[:config["max_jobs_per_day"]]

    print(f"Selected {len(filtered)} jobs.")

    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "jobs": filtered
    }

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    for i, job in enumerate(filtered, 1):
        print(
            f"{i}. {job['title']} | "
            f"{job['company']} | "
            f"Score: {job['score']}"
        )


if __name__ == "__main__":
    main()
