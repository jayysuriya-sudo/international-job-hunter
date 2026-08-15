import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

CONFIG_FILE = "config.json"


def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/2.0"
            }
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as error:
        print(f"Source failed: {url}")
        print(error)
        return None


def clean_html(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# --------------------------------------------------
# SOURCE 1 — ARBEITNOW
# --------------------------------------------------

def fetch_arbeitnow():

    url = "https://www.arbeitnow.com/api/job-board-api"

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for job in data.get("data", []):

        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": clean_html(job.get("description", "")),
            "source": "Arbeitnow"
        })

    return jobs


# --------------------------------------------------
# SOURCE 2 — REMOTIVE
# --------------------------------------------------

def fetch_remotive():

    url = "https://remotive.com/api/remote-jobs"

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for job in data.get("jobs", []):

        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("candidate_required_location", ""),
            "url": job.get("url", ""),
            "description": clean_html(job.get("description", "")),
            "source": "Remotive"
        })

    return jobs


# --------------------------------------------------
# SOURCE 3 — JOBICY
# --------------------------------------------------

def fetch_jobicy():

    url = "https://jobicy.com/api/v2/remote-jobs?count=50"

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for job in data.get("jobs", []):

        jobs.append({
            "title": job.get("jobTitle", ""),
            "company": job.get("companyName", ""),
            "location": job.get("jobGeo", ""),
            "url": job.get("url", ""),
            "description": clean_html(job.get("jobDescription", "")),
            "source": "Jobicy"
        })

    return jobs


# --------------------------------------------------
# JOB TITLE MATCHING
# --------------------------------------------------

def matches_title(job):

    title = job["title"].lower()

    keywords = [
        "videographer",
        "video editor",
        "video producer",
        "video production",
        "content creator",
        "content producer",
        "creative producer",
        "filmmaker",
        "film editor",
        "post production",
        "post-production",
        "multimedia producer",
        "multimedia editor",
        "social video",
        "social media video",
        "video content",
        "motion designer",
        "motion graphics",
        "motion graphic",
        "visual content",
        "digital content producer",
        "brand content",
        "creative content"
    ]

    return any(keyword in title for keyword in keywords)


# --------------------------------------------------
# EXCLUDED LOCATIONS
# --------------------------------------------------

def is_excluded(job, config):

    text = (
        job["location"]
        + " "
        + job["title"]
        + " "
        + job["description"]
    ).lower()

    for location in config["exclude_locations"]:

        if location.lower() in text:
            return True

    return False


# --------------------------------------------------
# LOCATION SCORE
# --------------------------------------------------

def location_score(job, config):

    text = (
        job["location"]
        + " "
        + job["description"]
    ).lower()

    score = 0

    preferred_locations = [
        "united kingdom",
        "uk",
        "london",
        "canada",
        "toronto",
        "vancouver",
        "australia",
        "sydney",
        "melbourne",
        "germany",
        "berlin",
        "munich",
        "netherlands",
        "amsterdam",
        "ireland",
        "dublin",
        "sweden",
        "france",
        "paris",
        "united states",
        "usa",
        "new york",
        "los angeles"
    ]

    for location in preferred_locations:

        if location in text:
            score += 5

    if "remote" in text:
        score += 15

    return score


# --------------------------------------------------
# SALARY DETECTION
# --------------------------------------------------

def salary_score(job):

    text = (
        job["title"]
        + " "
        + job["description"]
    ).lower()

    score = 0
    salary_found = ""

    salary_patterns = [
        r"\$[\d,]+(?:\s*-\s*\$?[\d,]+)?",
        r"£[\d,]+(?:\s*-\s*£?[\d,]+)?",
        r"€[\d,]+(?:\s*-\s*€?[\d,]+)?",
        r"\b\d{2,3}k(?:\s*-\s*\d{2,3}k)?"
    ]

    for pattern in salary_patterns:

        match = re.search(pattern, text)

        if match:

            salary_found = match.group(0)

            numbers = re.findall(
                r"\d+(?:,\d+)?",
                salary_found
            )

            if numbers:

                try:
                    highest = max(
                        int(number.replace(",", ""))
                        for number in numbers
                    )

                    if highest >= 50000:
                        score += 25

                    elif highest >= 40000:
                        score += 15

                    elif highest >= 30000:
                        score += 8

                except ValueError:
                    pass

            break

    job["salary"] = salary_found or "Not listed"

    return score


# --------------------------------------------------
# VISA / RELOCATION SCORE
# --------------------------------------------------

def international_score(job):

    text = (
        job["title"]
        + " "
        + job["description"]
    ).lower()

    keywords = [
        "visa sponsorship",
        "visa sponsor",
        "sponsorship available",
        "work visa",
        "work permit",
        "relocation",
        "relocation package",
        "relocation assistance",
        "immigration support"
    ]

    score = 0

    for keyword in keywords:

        if keyword in text:
            score += 15

    return score


# --------------------------------------------------
# SENIORITY SCORE
# --------------------------------------------------

def seniority_score(job):

    title = job["title"].lower()

    keywords = [
        "senior",
        "lead",
        "principal",
        "head",
        "manager",
        "director"
    ]

    score = 0

    for keyword in keywords:

        if keyword in title:
            score += 10

    return score


# --------------------------------------------------
# CREATIVE INDUSTRY SCORE
# --------------------------------------------------

def industry_score(job):

    text = (
        job["title"]
        + " "
        + job["description"]
    ).lower()

    keywords = [
        "film",
        "media",
        "advertising",
        "production",
        "creative",
        "entertainment",
        "technology",
        "brand",
        "marketing",
        "agency",
        "fashion",
        "sports"
    ]

    score = 0

    for keyword in keywords:

        if keyword in text:
            score += 3

    return score


# --------------------------------------------------
# FINAL JOB SCORE
# --------------------------------------------------

def score_job(job, config):

    score = 0

    title = job["title"].lower()

    # Strong title match
    if "senior" in title:
        score += 20

    if "lead" in title:
        score += 20

    if "producer" in title:
        score += 15

    if "video editor" in title:
        score += 25

    if "videographer" in title:
        score += 25

    if "content creator" in title:
        score += 20

    score += location_score(job, config)

    score += salary_score(job)

    score += international_score(job)

    score += seniority_score(job)

    score += industry_score(job)

    return score


# --------------------------------------------------
# MAIN SEARCH
# --------------------------------------------------

def main():

    print("====================================")
    print("🌍 INTERNATIONAL JOB HUNTER 2.0")
    print("====================================")

    config = load_config()

    all_jobs = []

    print("🔎 Searching Arbeitnow...")
    all_jobs.extend(fetch_arbeitnow())

    print("🔎 Searching Remotive...")
    all_jobs.extend(fetch_remotive())

    print("🔎 Searching Jobicy...")
    all_jobs.extend(fetch_jobicy())

    print(f"📊 Total jobs found: {len(all_jobs)}")

    filtered = []

    for job in all_jobs:

        if not job["title"]:
            continue

        if not job["url"]:
            continue

        if not matches_title(job):
            continue

        if is_excluded(job, config):
            continue

        job["score"] = score_job(job, config)

        filtered.append(job)

    # Remove duplicate URLs
    unique_jobs = {}

    for job in filtered:

        if job["url"] not in unique_jobs:
            unique_jobs[job["url"]] = job

    filtered = list(unique_jobs.values())

    # Highest quality jobs first
    filtered.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # Keep best jobs
    max_jobs = config.get(
        "max_jobs_per_day",
        10
    )

    filtered = filtered[:max_jobs]

    print(f"⭐ Strong matches: {len(filtered)}")

    # Save results
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "jobs": filtered
    }

    with open(
        "jobs.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    # Print results
    for number, job in enumerate(filtered, 1):

        print("")
        print(f"#{number}")
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Salary: {job['salary']}")
        print(f"Score: {job['score']}")
        print(f"Source: {job['source']}")
        print(f"URL: {job['url']}")


if __name__ == "__main__":
    main()
