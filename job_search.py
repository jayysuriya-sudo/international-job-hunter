import json
import os
import re
import urllib.request
from datetime import datetime, timezone

CONFIG_FILE = "config.json"
COMPANIES_FILE = "companies.json"


# ==================================================
# FILE HELPERS
# ==================================================

def load_json_file(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"Could not load {filename}: {error}")
        return default if default is not None else {}


# ==================================================
# WEB REQUEST
# ==================================================

def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/4.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as error:
        print(f"⚠️ Source unavailable: {url}")
        print(f"   {error}")
        return None


# ==================================================
# CLEAN TEXT
# ==================================================

def clean_html(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        str(text)
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ==================================================
# JOB KEYWORDS
# ==================================================

PRIMARY_ROLES = [
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
    "video director",
    "content director"
]

SECONDARY_ROLES = [
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
    "digital content producer"
]


def matches_title(title):

    title = title.lower()

    keywords = (
        PRIMARY_ROLES
        + SECONDARY_ROLES
    )

    return any(
        keyword in title
        for keyword in keywords
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
            "title": item.get(
                "title",
                ""
            ),
            "company": company,
            "location": item.get(
                "location",
                {}
            ).get(
                "name",
                ""
            ),
            "url": item.get(
                "absolute_url",
                ""
            ),
            "description": clean_html(
                item.get(
                    "content",
                    ""
                )
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

    if not isinstance(
        data,
        list
    ):
        return []

    jobs = []

    for item in data:

        categories = item.get(
            "categories",
            {}
        )

        jobs.append({
            "title": item.get(
                "text",
                ""
            ),
            "company": company,
            "location": categories.get(
                "location",
                ""
            ),
            "url": item.get(
                "hostedUrl",
                ""
            ),
            "description": clean_html(
                item.get(
                    "descriptionPlain",
                    ""
                )
            ),
            "source": "Lever"
        })

    return jobs


# ==================================================
# ASHBY
# ==================================================

def fetch_ashby(company):

    url = (
        "https://api.ashbyhq.com/"
        "posting-api/job-board/"
        + company
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get(
        "jobs",
        []
    ):

        jobs.append({
            "title": item.get(
                "title",
                ""
            ),
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

    url = (
        "https://remotive.com/api/"
        "remote-jobs"
    )

    data = get_json(url)

    if not data:
        return []

    jobs = []

    for item in data.get(
        "jobs",
        []
    ):

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
                "candidate_required_location",
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

    for item in data.get(
        "data",
        []
    ):

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

    for item in data.get(
        "jobs",
        []
    ):

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
# SALARY DETECTION
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

        if not match:
            continue

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

        if highest >= 100000:
            return 40

        if highest >= 80000:
            return 35

        if highest >= 70000:
            return 30

        if highest >= 60000:
            return 27

        if highest >= 50000:
            return 24

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

    visa_keywords = [
        "visa sponsorship",
        "visa sponsor",
        "visa support",
        "work visa",
        "work permit",
        "sponsorship available",
        "immigration support",
        "sponsor visa"
    ]

    relocation_keywords = [
        "relocation package",
        "relocation assistance",
        "relocation support",
        "relocation"
    ]

    score = 0

    for keyword in visa_keywords:

        if keyword in text:
            score += 20

    for keyword in relocation_keywords:

        if keyword in text:
            score += 10

    return score


# ==================================================
# LOCATION SCORE
# ==================================================

def location_score(job):

    text = (
        job.get("location", "")
        + " "
        + job.get("description", "")
    ).lower()

    countries = [
        "united kingdom",
        "uk",
        "london",
        "england",
        "scotland",
        "canada",
        "toronto",
        "vancouver",
        "montreal",
        "australia",
        "sydney",
        "melbourne",
        "brisbane",
        "united states",
        "usa",
        "new york",
        "los angeles",
        "san francisco",
        "germany",
        "berlin",
        "munich",
        "netherlands",
        "amsterdam",
        "ireland",
        "dublin",
        "sweden",
        "stockholm",
        "france",
        "paris",
        "singapore",
        "new zealand"
    ]

    score = 0

    for country in countries:

        if country in text:
            score += 5

    if "remote" in text:
        score += 20

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
# ROLE RELEVANCE
# ==================================================

def role_score(job):

    title = job.get(
        "title",
        ""
    ).lower()

    score = 0

    # Highest priority
    if "video editor" in title:
        score += 35

    if "videographer" in title:
        score += 35

    if "video producer" in title:
        score += 35

    # Very relevant
    if "content producer" in title:
        score += 30

    if "creative producer" in title:
        score += 30

    if "content creator" in title:
        score += 28

    if "filmmaker" in title:
        score += 28

    if "film editor" in title:
        score += 28

    # Relevant
    if "motion designer" in title:
        score += 22

    if "motion graphics" in title:
        score += 22

    if "post production" in title:
        score += 22

    if "multimedia" in title:
        score += 20

    if "social video" in title:
        score += 20

    if "brand content" in title:
        score += 20

    return score


# ==================================================
# SKILL / INDUSTRY RELEVANCE
# ==================================================

def skill_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    skills = [
        "premiere pro",
        "adobe premiere",
        "after effects",
        "davinci resolve",
        "final cut pro",
        "capcut",
        "cinematography",
        "camera",
        "lighting",
        "editing",
        "video editing",
        "storytelling",
        "production",
        "post production",
        "content production",
        "social media",
        "instagram",
        "youtube",
        "commercial",
        "advertising",
        "brand content"
    ]

    score = 0

    for skill in skills:

        if skill in text:
            score += 2

    return min(
        score,
        20
    )


# ==================================================
# COMPANY / INDUSTRY QUALITY
# ==================================================

def industry_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    industries = [
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
        "sports",
        "streaming",
        "studio"
    ]

    score = 0

    for industry in industries:

        if industry in text:
            score += 3

    return min(
        score,
        15
    )


# ==================================================
# DIRECT EMPLOYER BONUS
# ==================================================

def source_score(job):

    source = job.get(
        "source",
        ""
    )

    if source in [
        "Greenhouse",
        "Lever",
        "Ashby"
    ]:
        return 10

    return 0


# ==================================================
# FINAL PERSONALIZED SCORE
# ==================================================

def score_job(job):

    total = 0

    total += role_score(job)

    total += salary_score(job)

    total += international_score(job)

    total += location_score(job)

    total += seniority_score(job)

    total += skill_score(job)

    total += industry_score(job)

    total += source_score(job)

    # Keep score readable
    job["score"] = min(
        total,
        100
    )

    # Classification
    score = job["score"]

    if score >= 90:
        job["rating"] = "🔥 EXCELLENT"

    elif score >= 75:
        job["rating"] = "🟢 STRONG"

    elif score >= 60:
        job["rating"] = "🟡 REVIEW"

    else:
        job["rating"] = "⚪ LOW"

    return job["score"]


# ==================================================
# MAIN
# ==================================================

def main():

    print(
        "=========================================="
    )

    print(
        "🌍 INTERNATIONAL JOB HUNTER 4.0"
    )

    print(
        "=========================================="
    )

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
    # COMPANY CAREER BOARDS
    # ------------------------------------------

    print("")
    print(
        "🏢 SEARCHING COMPANY CAREER BOARDS"
    )

    print(
        "------------------------------------------"
    )

    for company in companies.get(
        "greenhouse",
        []
    ):

        print(
            f"🔎 Greenhouse: {company}"
        )

        all_jobs.extend(
            fetch_greenhouse(
                company
            )
        )

    for company in companies.get(
        "lever",
        []
    ):

        print(
            f"🔎 Lever: {company}"
        )

        all_jobs.extend(
            fetch_lever(
                company
            )
        )

    for company in companies.get(
        "ashby",
        []
    ):

        print(
            f"🔎 Ashby: {company}"
        )

        all_jobs.extend(
            fetch_ashby(
                company
            )
        )

    # ------------------------------------------
    # GENERAL JOB BOARDS
    # ------------------------------------------

    print("")
    print(
        "🌐 SEARCHING GENERAL JOB BOARDS"
    )

    print(
        "------------------------------------------"
    )

    print(
        "🔎 Remotive..."
    )

    all_jobs.extend(
        fetch_remotive()
    )

    print(
        "🔎 Arbeitnow..."
    )

    all_jobs.extend(
        fetch_arbeitnow()
    )

    print(
        "🔎 Jobicy..."
    )

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

        title = job.get(
            "title",
            ""
        )

        if not title:
            continue

        if not job.get(
            "url",
            ""
        ):
            continue

        if not matches_title(
            title
        ):
            continue

        if is_excluded(
            job,
            config
        ):
            continue

        score_job(job)

        # Don't send weak matches
        if job["score"] < 60:
            continue

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
    # SORT BEST FIRST
    # ------------------------------------------

    filtered.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # ------------------------------------------
    # TOP JOBS
    # ------------------------------------------

    max_jobs = config.get(
        "max_jobs_per_day",
        10
    )

    # Allow up to 15 good opportunities
    max_jobs = max(
        max_jobs,
        15
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
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total_jobs_found":
            len(all_jobs),

        "strong_matches":
            len(filtered),

        "jobs":
            filtered
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
    # PRINT RESULTS
    # ------------------------------------------

    for number, job in enumerate(
        filtered,
        1
    ):

        print("")
        print(
            f"#{number} "
            f"{job['rating']}"
        )

        print(
            f"💼 {job['title']}"
        )

        print(
            f"🏢 {job['company']}"
        )

        print(
            f"📍 {job['location']}"
        )

        print(
            f"💰 {job.get('salary', 'Not listed')}"
        )

        print(
            f"⭐ Score: "
            f"{job['score']}/100"
        )

        print(
            f"🔎 {job['source']}"
        )

        print(
            f"🔗 {job['url']}"
        )

    print("")
    print(
        "✅ JOB SEARCH COMPLETE"
    )


if __name__ == "__main__":
    main()
