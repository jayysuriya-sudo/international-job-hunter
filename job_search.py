import json
import re
import urllib.request
from datetime import datetime, timezone

CONFIG_FILE = "config.json"
COMPANIES_FILE = "companies.json"


# ============================================================
# FILE HELPERS
# ============================================================

def load_json_file(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"Could not load {filename}: {error}")
        return default if default is not None else {}


# ============================================================
# HTTP / JSON
# ============================================================

def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/5.0",
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


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_html(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        str(text)
    )

    text = re.sub(
        r"&nbsp;",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"&amp;",
        "&",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# JOB KEYWORDS
# ============================================================

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
    "content director",
    "motion designer",
    "motion design",
    "motion graphics designer",
    "motion graphics"
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
    "visual content",
    "digital content producer",
    "video content producer",
    "creative video",
    "content production"
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


# ============================================================
# EXCLUDED LOCATIONS
# ============================================================

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


# ============================================================
# GREENHOUSE
# ============================================================

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
            "id": item.get("id"),
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
            "source": "Greenhouse",
            "greenhouse_company": company
        })

    return jobs


# ============================================================
# GREENHOUSE PAY TRANSPARENCY
# ============================================================

def enrich_greenhouse_salary(job):

    job_id = job.get("id")
    company = job.get(
        "greenhouse_company",
        ""
    )

    if not job_id or not company:
        return job

    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        + company
        + "/jobs/"
        + str(job_id)
        + "?pay_transparency=true"
    )

    data = get_json(url)

    if not data:
        return job

    # Replace description with detailed description
    detailed_description = data.get(
        "content",
        ""
    )

    if detailed_description:
        job["description"] = clean_html(
            detailed_description
        )

    pay_ranges = data.get(
        "pay_input_ranges",
        []
    )

    if not pay_ranges:
        return job

    # Keep all available ranges
    ranges = []

    for pay in pay_ranges:

        minimum = pay.get(
            "min_cents"
        )

        maximum = pay.get(
            "max_cents"
        )

        currency = pay.get(
            "currency_type",
            "USD"
        )

        if minimum is None and maximum is None:
            continue

        minimum_value = (
            minimum / 100
            if minimum is not None
            else None
        )

        maximum_value = (
            maximum / 100
            if maximum is not None
            else None
        )

        ranges.append({
            "min": minimum_value,
            "max": maximum_value,
            "currency": currency,
            "title": pay.get(
                "title",
                ""
            ),
            "blurb": pay.get(
                "blurb",
                ""
            )
        })

    if ranges:

        job["pay_ranges"] = ranges

        # Use first range as primary display
        primary = ranges[0]

        minimum = primary["min"]
        maximum = primary["max"]
        currency = primary["currency"]

        if minimum is not None and maximum is not None:

            job["salary"] = (
                f"{format_money(minimum, currency)}"
                f" – "
                f"{format_money(maximum, currency)}"
                f" / year"
            )

        elif minimum is not None:

            job["salary"] = (
                f"From "
                f"{format_money(minimum, currency)}"
                f" / year"
            )

        elif maximum is not None:

            job["salary"] = (
                f"Up to "
                f"{format_money(maximum, currency)}"
                f" / year"
            )

    return job


# ============================================================
# MONEY FORMAT
# ============================================================

def format_money(value, currency):

    symbols = {
        "USD": "$",
        "CAD": "C$",
        "AUD": "A$",
        "GBP": "£",
        "EUR": "€",
        "SGD": "S$",
        "NZD": "NZ$"
    }

    symbol = symbols.get(
        currency,
        currency + " "
    )

    if value >= 1000:

        return (
            symbol
            + f"{value:,.0f}"
        )

    return (
        symbol
        + f"{value:,.2f}"
    )


# ============================================================
# LEVER
# ============================================================

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


# ============================================================
# ASHBY
# ============================================================

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


# ============================================================
# REMOTIVE
# ============================================================

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


# ============================================================
# ARBEITNOW
# ============================================================

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


# ============================================================
# JOBICY
# ============================================================

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


# ============================================================
# SALARY DETECTION
# ============================================================

def detect_salary_from_text(text):

    patterns = [
        (
            r"\$[\d,]+(?:\.\d+)?"
            r"(?:\s*[-–]\s*\$?[\d,]+(?:\.\d+)?)?"
        ),
        (
            r"£[\d,]+(?:\.\d+)?"
            r"(?:\s*[-–]\s*£?[\d,]+(?:\.\d+)?)?"
        ),
        (
            r"€[\d,]+(?:\.\d+)?"
            r"(?:\s*[-–]\s*€?[\d,]+(?:\.\d+)?)?"
        ),
        (
            r"\b\d{2,3}k"
            r"(?:\s*[-–]\s*\d{2,3}k)?"
        )
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(0)

    return None


def salary_score(job):

    # Greenhouse structured salary
    pay_ranges = job.get(
        "pay_ranges",
        []
    )

    if pay_ranges:

        highest_value = 0

        for pay in pay_ranges:

            minimum = pay.get(
                "min"
            ) or 0

            maximum = pay.get(
                "max"
            ) or 0

            highest_value = max(
                highest_value,
                minimum,
                maximum
            )

        currency = pay_ranges[0].get(
            "currency",
            "USD"
        )

        # Store approximate numeric value
        job["salary_max_value"] = (
            highest_value
        )

        # Strong scoring
        if highest_value >= 150000:
            return 40

        if highest_value >= 120000:
            return 38

        if highest_value >= 100000:
            return 35

        if highest_value >= 80000:
            return 32

        if highest_value >= 70000:
            return 28

        if highest_value >= 60000:
            return 24

        if highest_value >= 50000:
            return 20

        if highest_value >= 40000:
            return 14

        return 8

    # Text-based salary detection
    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    )

    salary = detect_salary_from_text(
        text
    )

    if salary:

        job["salary"] = salary

        numbers = re.findall(
            r"\d+(?:,\d+)?",
            salary
        )

        highest = 0

        for number in numbers:

            try:

                value = int(
                    number.replace(
                        ",",
                        ""
                    )
                )

                # Convert k values
                if "k" in salary.lower():
                    value *= 1000

                highest = max(
                    highest,
                    value
                )

            except ValueError:
                pass

        job["salary_max_value"] = highest

        if highest >= 150000:
            return 40

        if highest >= 120000:
            return 38

        if highest >= 100000:
            return 35

        if highest >= 80000:
            return 32

        if highest >= 70000:
            return 28

        if highest >= 60000:
            return 24

        if highest >= 50000:
            return 20

        if highest >= 40000:
            return 14

        return 8

    job["salary"] = "Not listed"
    job["salary_max_value"] = 0

    return 0


# ============================================================
# VISA / RELOCATION
# ============================================================

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
        "sponsor visa",
        "visa assistance"
    ]

    relocation_keywords = [
        "relocation package",
        "relocation assistance",
        "relocation support",
        "relocation"
    ]

    no_sponsorship_keywords = [
        "no visa sponsorship",
        "without sponsorship",
        "unable to sponsor",
        "will not sponsor",
        "does not sponsor",
        "not eligible for sponsorship"
    ]

    for keyword in no_sponsorship_keywords:

        if keyword in text:

            job["visa_status"] = (
                "🚫 Sponsorship not available"
            )

            return -10

    visa_found = False
    relocation_found = False

    for keyword in visa_keywords:

        if keyword in text:

            visa_found = True
            break

    for keyword in relocation_keywords:

        if keyword in text:

            relocation_found = True
            break

    score = 0

    if visa_found:

        job["visa_status"] = (
            "🛂 Sponsorship mentioned"
        )

        score += 25

    else:

        job["visa_status"] = (
            "❓ Not mentioned"
        )

    if relocation_found:

        job["relocation_status"] = (
            "✈️ Relocation mentioned"
        )

        score += 10

    else:

        job["relocation_status"] = (
            "❓ Not mentioned"
        )

    return score


# ============================================================
# LOCATION SCORE
# ============================================================

def location_score(job):

    text = (
        job.get("location", "")
        + " "
        + job.get("description", "")
    ).lower()

    preferred_locations = [
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

    for location in preferred_locations:

        if location in text:

            score += 5

    if "remote" in text:

        score += 20

    return score


# ============================================================
# SENIORITY
# ============================================================

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


# ============================================================
# ROLE SCORE
# ============================================================

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

    # Strong
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

    # Motion
    if "motion designer" in title:
        score += 30

    if "motion design" in title:
        score += 28

    if "motion graphics" in title:
        score += 28

    # Other relevant roles
    if "post production" in title:
        score += 22

    if "multimedia" in title:
        score += 20

    if "social video" in title:
        score += 20

    if "brand content" in title:
        score += 20

    return score


# ============================================================
# SKILLS
# ============================================================

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
        "cinema 4d",
        "houdini",
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
        "brand content",
        "motion graphics",
        "motion design"
    ]

    score = 0
    matched = []

    for skill in skills:

        if skill in text:

            score += 2
            matched.append(
                skill
            )

    job["matched_skills"] = matched[:8]

    return min(
        score,
        20
    )


# ============================================================
# INDUSTRY SCORE
# ============================================================

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
        "studio",
        "experiential",
        "events"
    ]

    score = 0

    for industry in industries:

        if industry in text:

            score += 3

    return min(
        score,
        15
    )


# ============================================================
# DIRECT EMPLOYER BONUS
# ============================================================

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


# ============================================================
# MATCH REASONS
# ============================================================

def build_match_reasons(job):

    reasons = []

    title = job.get(
        "title",
        ""
    ).lower()

    description = job.get(
        "description",
        ""
    ).lower()

    if (
        "video editor" in title
        or "videographer" in title
        or "video producer" in title
    ):

        reasons.append(
            "🎥 Strong video role"
        )

    elif (
        "motion designer" in title
        or "motion design" in title
        or "motion graphics" in title
    ):

        reasons.append(
            "🎨 Motion/visual design role"
        )

    elif (
        "content" in title
        or "creative" in title
    ):

        reasons.append(
            "🎬 Creative/content role"
        )

    if job.get(
        "salary_max_value",
        0
    ) >= 100000:

        reasons.append(
            "💰 High salary"
        )

    elif job.get(
        "salary_max_value",
        0
    ) >= 70000:

        reasons.append(
            "💰 Strong salary"
        )

    if (
        "visa_status" in job
        and "Sponsorship mentioned"
        in job["visa_status"]
    ):

        reasons.append(
            "🛂 Sponsorship mentioned"
        )

    if (
        "relocation_status" in job
        and "Relocation mentioned"
        in job["relocation_status"]
    ):

        reasons.append(
            "✈️ Relocation mentioned"
        )

    if "remote" in (
        job.get(
            "location",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
    ).lower():

        reasons.append(
            "🏠 Remote opportunity"
        )

    if (
        "senior" in title
        or "lead" in title
        or "director" in title
        or "manager" in title
    ):

        reasons.append(
            "🧑‍💼 Senior-level opportunity"
        )

    if (
        "after effects" in description
        or "premiere pro" in description
        or "cinema 4d" in description
        or "houdini" in description
    ):

        reasons.append(
            "🛠️ Relevant creative software"
        )

    if (
        "film" in description
        or "production" in description
        or "advertising" in description
        or "brand" in description
    ):

        reasons.append(
            "🏢 Creative/media industry"
        )

    return reasons[:6]


# ============================================================
# FINAL SCORE
# ============================================================

def score_job(job):

    total = 0

    total += role_score(
        job
    )

    total += salary_score(
        job
    )

    total += international_score(
        job
    )

    total += location_score(
        job
    )

    total += seniority_score(
        job
    )

    total += skill_score(
        job
    )

    total += industry_score(
        job
    )

    total += source_score(
        job
    )

    # Cap at 100
    job["score"] = min(
        total,
        100
    )

    if job["score"] >= 90:

        job["rating"] = (
            "🔥 EXCELLENT"
        )

    elif job["score"] >= 75:

        job["rating"] = (
            "🟢 STRONG"
        )

    elif job["score"] >= 60:

        job["rating"] = (
            "🟡 REVIEW"
        )

    else:

        job["rating"] = (
            "⚪ LOW"
        )

    job["match_reasons"] = (
        build_match_reasons(
            job
        )
    )

    return job["score"]


# ============================================================
# ENRICH GREENHOUSE JOBS
# ============================================================

def enrich_matching_greenhouse_jobs(
    jobs
):

    enriched = []

    for job in jobs:

        # Only spend API calls on relevant jobs
        if not matches_title(
            job.get(
                "title",
                ""
            )
        ):

            continue

        print(
            "💰 Checking salary: "
            + job.get(
                "title",
                ""
            )
        )

        enriched_job = (
            enrich_greenhouse_salary(
                job
            )
        )

        enriched.append(
            enriched_job
        )

    return enriched


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "🌍 INTERNATIONAL JOB HUNTER 5.0"
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

    # ========================================================
    # COMPANY CAREER BOARDS
    # ========================================================

    print("")
    print(
        "🏢 SEARCHING COMPANY CAREER BOARDS"
    )

    print(
        "------------------------------------------"
    )

    # ---------------- GREENHOUSE ----------------

    greenhouse_jobs = []

    for company in companies.get(
        "greenhouse",
        []
    ):

        print(
            f"🔎 Greenhouse: {company}"
        )

        jobs = fetch_greenhouse(
            company
        )

        greenhouse_jobs.extend(
            jobs
        )

    print("")
    print(
        "💰 CHECKING PAY TRANSPARENCY "
        "FOR RELEVANT GREENHOUSE JOBS"
    )

    greenhouse_jobs = (
        enrich_matching_greenhouse_jobs(
            greenhouse_jobs
        )
    )

    all_jobs.extend(
        greenhouse_jobs
    )

    # ---------------- LEVER ----------------

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

    # ---------------- ASHBY ----------------

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

    # ========================================================
    # GENERAL JOB BOARDS
    # ========================================================

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

    # ========================================================
    # TOTAL
    # ========================================================

    print("")
    print(
        f"📊 TOTAL JOBS FOUND: "
        f"{len(all_jobs)}"
    )

    # ========================================================
    # FILTER
    # ========================================================

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

        score_job(
            job
        )

        # Minimum quality
        if job["score"] < 60:
            continue

        filtered.append(
            job
        )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

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

    # ========================================================
    # SORT
    # ========================================================

    filtered.sort(
        key=lambda job: (
            job.get(
                "score",
                0
            ),
            job.get(
                "salary_max_value",
                0
            )
        ),
        reverse=True
    )

    # ========================================================
    # LIMIT
    # ========================================================

    configured_limit = config.get(
        "max_jobs_per_day",
        10
    )

    # Minimum 15 if there are enough
    max_jobs = max(
        configured_limit,
        15
    )

    filtered = filtered[
        :max_jobs
    ]

    # ========================================================
    # RESULTS
    # ========================================================

    print("")
    print(
        f"⭐ STRONG MATCHES: "
        f"{len(filtered)}"
    )

    # ========================================================
    # SAVE
    # ========================================================

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

    # ========================================================
    # PRINT TOP RESULTS
    # ========================================================

    print("")

    for number, job in enumerate(
        filtered,
        1
    ):

        print(
            f"#{number} "
            f"{job.get('rating', '')}"
        )

        print(
            f"💼 {job.get('title', '')}"
        )

        print(
            f"🏢 {job.get('company', '')}"
        )

        print(
            f"📍 {job.get('location', '')}"
        )

        print(
            f"💰 {job.get('salary', 'Not listed')}"
        )

        print(
            f"⭐ Score: "
            f"{job.get('score', 0)}/100"
        )

        print(
            f"🛂 "
            f"{job.get('visa_status', '❓ Not mentioned')}"
        )

        print(
            f"✈️ "
            f"{job.get('relocation_status', '❓ Not mentioned')}"
        )

        print(
            f"🔎 {job.get('source', '')}"
        )

        print(
            f"🔗 {job.get('url', '')}"
        )

        reasons = job.get(
            "match_reasons",
            []
        )

        if reasons:

            print(
                "Why it matches:"
            )

            for reason in reasons:

                print(
                    f"  {reason}"
                )

        print(
            "------------------------------------------"
        )

    print("")
    print(
        "✅ JOB SEARCH COMPLETE"
    )


if __name__ == "__main__":
    main()
