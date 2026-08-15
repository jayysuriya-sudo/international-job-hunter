import json
import os
import re
import urllib.request
from datetime import datetime


CONFIG_FILE = "config.json"
COMPANIES_FILE = "companies.json"


# ==================================================
# BASIC HELPERS
# ==================================================

def load_json_file(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"Could not load {filename}: {error}")
        return default if default is not None else {}


def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/3.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as error:
        print(f"⚠️ Source unavailable: {url}")
        print(f"   {error}")
        return None


def clean_html(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==================================================
# JOB TITLE MATCHING
# ==================================================

JOB_KEYWORDS = [
    "videographer",
    "video editor",
    "senior video editor",
    "video producer",
    "senior video producer",
    "content creator",
    "content producer",
    "creative producer",
    "film editor",
    "filmmaker",
    "post production",
    "post-production",
    "multimedia producer",
    "multimedia editor",
    "video content",
    "social video",
    "social media video",
    "brand content",
    "brand video",
    "creative content",
    "motion designer",
    "motion graphics",
    "motion graphic",
    "visual content",
    "digital content producer",
    "video director",
    "content director"
]


def matches_title(title):
    title = title.lower()

    return any(
        keyword in title
        for keyword in JOB_KEYWORDS
    )


# ==================================================
# EXCLUDED LOCATIONS
# ==================================================

def is_excluded(job, config):

    text = (
        job.get("title", "")
        + " "
        + job.get("location", "")
        + " "
        + job.get("description", "")
    ).lower()

    excluded = config.get(
        "exclude_locations",
        []
    )

    for location in excluded:

        if location.lower() in text:
            return True

    return False


# ==================================================
# GREENHOUSE
# ==================================================

def fetch_greenhouse(company):

    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        + company
        + "/jobs?content=true"
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get("jobs", []):

        jobs.append({
            "title": item.get("title", ""),
            "company": company,
            "location": (
                item.get("location", {})
                .get("name", "")
            ),
            "url": item.get("absolute_url", ""),
            "description": clean_html(
                item.get("content", "")
            ),
            "source": "Greenhouse"
        })

    return jobs


# ==================================================
# LEVER
# ==================================================

def fetch_lever(company):

    url = (
        "https://api.lever.co/v0/postings/"
        + company
        + "?mode=json"
    )

    data = get_json(url)

    if not isinstance(data, list):
        return []

    jobs = []

    for item in data:

        categories = item.get(
            "categories",
            {}
        )

        location = categories.get(
            "location",
            ""
        )

        jobs.append({
            "title": item.get("text", ""),
            "company": company,
            "location": location,
            "url": item.get("hostedUrl", ""),
            "description": clean_html(
                item.get("descriptionPlain", "")
            ),
            "source": "Lever"
        })

    return jobs


# ==================================================
# ASHBY
# ==================================================

def fetch_ashby(company):

    url = (
        "https://api.ashbyhq.com/posting-api/"
        "job-board/"
        + company
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get("jobs", []):

        jobs.append({
            "title": item.get("title", ""),
            "company": company,
            "location": item.get(
                "location",
                ""
            ),
            "url": item.get(
                "jobUrl",
                ""
            ),
            "description": clean_html(
                item.get(
                    "descriptionPlain",
                    item.get(
                        "description",
                        ""
                    )
                )
            ),
            "source": "Ashby"
        })

    return jobs


# ==================================================
# REMOTIVE
# ==================================================

def fetch_remotive():

    url = "https://remotive.com/api/remote-jobs"

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get("jobs", []):

        jobs.append({
            "title": item.get("title", ""),
            "company": item.get(
                "company_name",
                ""
            ),
            "location": item.get(
                "candidate_required_location",
                ""
            ),
            "url": item.get("url", ""),
            "description": clean_html(
                item.get("description", "")
            ),
            "source": "Remotive"
        })

    return jobs


# ==================================================
# ARBEITNOW
# ==================================================

def fetch_arbeitnow():

    url = (
        "https://www.arbeitnow.com/"
        "api/job-board-api"
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get("data", []):

        jobs.append({
            "title": item.get(
                "title",
                ""
            ),
            "company": item.get(
                "company_name",
                ""
            ),
            "location": item.get(
                "location",
                ""
            ),
            "url": item.get(
                "url",
                ""
            ),
            "description": clean_html(
                item.get(
                    "description",
                    ""
                )
            ),
            "source": "Arbeitnow"
        })

    return jobs


# ==================================================
# JOBICY
# ==================================================

def fetch_jobicy():

    url = (
        "https://jobicy.com/api/v2/"
        "remote-jobs?count=50"
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get("jobs", []):

        jobs.append({
            "title": item.get(
                "jobTitle",
                ""
            ),
            "company": item.get(
                "companyName",
                ""
            ),
            "location": item.get(
                "jobGeo",
                ""
            ),
            "url": item.get(
                "url",
                ""
            ),
            "description": clean_html(
                item.get(
                    "jobDescription",
                    ""
                )
            ),
            "source": "Jobicy"
        })

    return jobs


# ==================================================
# SALARY
# ==================================================

def salary_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    )

    patterns = [
        r"\$[\d,]+(?:\s*-\s*\$?[\d,]+)?",
        r"£[\d,]+(?:\s*-\s*£?[\d,]+)?",
        r"€[\d,]+(?:\s*-\s*€?[\d,]+)?",
        r"\b\d{2,3}k(?:\s*-\s*\d{2,3}k)?"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            salary = match.group(0)

            numbers = re.findall(
                r"\d+(?:,\d+)?",
                salary
            )

            highest = 0

            for number in numbers:
                try:
                    highest = max(
                        highest,
                        int(
                            number.replace(
                                ",",
                                ""
                            )
                        )
                    )
                except ValueError:
                    pass

            job["salary"] = salary

            if highest >= 70000:
                return 35

            if highest >= 50000:
                return 25

            if highest >= 40000:
                return 15

            if highest >= 30000:
                return 8

            return 3

    job["salary"] = "Not listed"

    return 0


# ==================================================
# VISA / RELOCATION
# ==================================================

def international_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    keywords = [
        "visa sponsorship",
        "visa sponsor",
        "visa support",
        "work visa",
        "work permit",
        "sponsorship available",
        "immigration support",
        "relocation package",
        "relocation assistance",
        "relocation support",
        "relocation"
    ]

    score = 0

    for keyword in keywords:

        if keyword in text:
            score += 15

    return score


# ==================================================
# LOCATION
# ==================================================

def location_score(job):

    text = (
        job.get("location", "")
        + " "
        + job.get("description", "")
    ).lower()

    preferred = [
        "united kingdom",
        "uk",
        "london",
        "canada",
        "toronto",
        "vancouver",
        "australia",
        "sydney",
        "melbourne",
        "united states",
        "usa",
        "new york",
        "los angeles",
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
        "singapore",
        "new zealand"
    ]

    score = 0

    for location in preferred:

        if location in text:
            score += 5

    if "remote" in text:
        score += 15

    return score


# ==================================================
# SENIORITY
# ==================================================

def seniority_score(job):

    title = job.get(
        "title",
        ""
    ).lower()

    score = 0

    if "senior" in title:
        score += 15

    if "lead" in title:
        score += 18

    if "principal" in title:
        score += 18

    if "head" in title:
        score += 20

    if "manager" in title:
        score += 18

    if "director" in title:
        score += 20

    return score


# ==================================================
# CREATIVE INDUSTRY
# ==================================================

def industry_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
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


# ==================================================
# FINAL SCORE
# ==================================================

def score_job(job):

    title = job.get(
        "title",
        ""
    ).lower()

    score = 0

    if "videographer" in title:
        score += 30

    if "video editor" in title:
        score += 30

    if "video producer" in title:
        score += 30

    if "content creator" in title:
        score += 25

    if "content producer" in title:
        score += 25

    if "creative producer" in title:
        score += 25

    if "filmmaker" in title:
        score += 25

    if "motion designer" in title:
        score += 20

    score += salary_score(job)
    score += international_score(job)
    score += location_score(job)
    score += seniority_score(job)
    score += industry_score(job)

    return score


# ==================================================
# MAIN
# ==================================================

def main():

    print("==========================================")
    print("🌍 INTERNATIONAL JOB HUNTER 3.0")
    print("==========================================")

    config = load_json_file(
        CONFIG_FILE,
        {}
    )

    companies = load_json_file(
        COMPANIES_FILE,
        {}
    )

    all_jobs = []

    # ------------------------------------------
    # COMPANY BOARDS
    # ------------------------------------------

    print("")
    print("🏢 SEARCHING COMPANY CAREER BOARDS")
    print("------------------------------------------")

    greenhouse = companies.get(
        "greenhouse",
        []
    )

    for company in greenhouse:

        print(
            f"🔎 Greenhouse: {company}"
        )

        jobs = fetch_greenhouse(
            company
        )

        all_jobs.extend(jobs)

    lever = companies.get(
        "lever",
        []
    )

    for company in lever:

        print(
            f"🔎 Lever: {company}"
        )

        jobs = fetch_lever(
            company
        )

        all_jobs.extend(jobs)

    ashby = companies.get(
        "ashby",
        []
    )

    for company in ashby:

        print(
            f"🔎 Ashby: {company}"
        )

        jobs = fetch_ashby(
            company
        )

        all_jobs.extend(jobs)

    # ------------------------------------------
    # GENERAL JOB BOARDS
    # ------------------------------------------

    print("")
    print("🌐 SEARCHING GENERAL JOB BOARDS")
    print("------------------------------------------")

    print("🔎 Remotive...")
    all_jobs.extend(
        fetch_remotive()
    )

    print("🔎 Arbeitnow...")
    all_jobs.extend(
        fetch_arbeitnow()
    )

    print("🔎 Jobicy...")
    all_jobs.extend(
        fetch_jobicy()
    )

    print("")
    print(
        f"📊 TOTAL JOBS FOUND: "
        f"{len(all_jobs)}"
    )

    # ------------------------------------------
    # FILTER
    # ------------------------------------------

    filtered = []

    for job in all_jobs:

        if not job.get("title"):
            continue

        if not job.get("url"):
            continue

        if not matches_title(
            job["title"]
        ):
            continue

        if is_excluded(
            job,
            config
        ):
            continue

        job["score"] = score_job(
            job
        )

        filtered.append(job)

    # ------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------

    unique = {}

    for job in filtered:

        url = job.get(
            "url",
            ""
        )

        if url and url not in unique:
            unique[url] = job

    filtered = list(
        unique.values()
    )

    # ------------------------------------------
    # SORT
    # ------------------------------------------

    filtered.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    max_jobs = config.get(
        "max_jobs_per_day",
        10
    )

    filtered = filtered[
        :max_jobs
    ]

    print("")
    print(
        f"⭐ STRONG MATCHES: "
        f"{len(filtered)}"
    )

    # ------------------------------------------
    # SAVE RESULTS
    # ------------------------------------------

    output = {
        "generated_at":
            datetime.utcnow().isoformat(),
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

    # ------------------------------------------
    # PRINT TOP JOBS
    # ------------------------------------------

    for number, job in enumerate(
        filtered,
        1
    ):

        print("")
        print(
            f"#{number} "
            f"{job['title']}"
        )

        print(
            f"Company: "
            f"{job['company']}"
        )

        print(
            f"Location: "
            f"{job['location']}"
        )

        print(
            f"Salary: "
            f"{job.get('salary', 'Not listed')}"
        )

        print(
            f"Score: "
            f"{job['score']}"
        )

        print(
            f"Source: "
            f"{job['source']}"
        )

        print(
            f"URL: "
            f"{job['url']}"
        )

    print("")
    print("✅ JOB SEARCH COMPLETE")


if __name__ == "__main__":
    main()
