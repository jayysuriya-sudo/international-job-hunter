import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape


CONFIG_FILE = "config.json"
COMPANIES_FILE = "companies.json"


# ============================================================
# BASIC HELPERS
# ============================================================

def load_json_file(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"⚠️ Could not load {filename}: {error}")
        return default if default is not None else {}


def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/6.0",
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

    text = unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# ROLE CONFIGURATION
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
    "motion graphics designer"
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
    "motion graphics",
    "motion graphic",
    "visual content",
    "digital content producer",
    "experiential designer",
    "creative designer",
    "creative technologist"
]


def matches_title(title):
    title = title.lower()

    return any(
        keyword in title
        for keyword in PRIMARY_ROLES + SECONDARY_ROLES
    )


# ============================================================
# EXCLUDED LOCATIONS
# ============================================================

DEFAULT_EXCLUDED_LOCATIONS = [
    "dubai",
    "united arab emirates",
    "uae",
    "abu dhabi",
    "qatar",
    "doha",
    "saudi arabia",
    "riyadh",
    "jeddah",
    "kuwait",
    "bahrain",
    "manama",
    "oman",
    "muscat"
]


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
        DEFAULT_EXCLUDED_LOCATIONS
    )

    for location in excluded:
        if location.lower() in text:
            return True

    return False


# ============================================================
# SALARY FORMATTING
# ============================================================

CURRENCY_SYMBOLS = {
    "USD": "$",
    "CAD": "C$",
    "AUD": "A$",
    "GBP": "£",
    "EUR": "€",
    "SGD": "S$",
    "NZD": "NZ$",
    "CHF": "CHF ",
    "INR": "₹"
}


def format_money(amount, currency):

    symbol = CURRENCY_SYMBOLS.get(
        currency.upper(),
        currency.upper() + " "
    )

    return f"{symbol}{amount:,.0f}"


def format_greenhouse_salary(pay_ranges):

    if not pay_ranges:
        return None

    results = []

    for pay in pay_ranges:

        minimum = pay.get("min_cents")
        maximum = pay.get("max_cents")
        currency = pay.get(
            "currency_type",
            "USD"
        )

        if minimum is None or maximum is None:
            continue

        minimum /= 100
        maximum /= 100

        salary = (
            f"{format_money(minimum, currency)} - "
            f"{format_money(maximum, currency)} / year"
        )

        title = pay.get("title")

        if title:
            salary = f"{salary}"

        results.append(salary)

    if results:
        return " | ".join(results)

    return None


# ============================================================
# SALARY EXTRACTION FROM TEXT
# ============================================================

def extract_salary_values(text):

    if not text:
        return []

    text = unescape(text)

    values = []

    # $175,200 - $262,800
    currency_pattern = re.compile(
        r"(?P<currency>\$|£|€|C\$|A\$|S\$|NZ\$|₹)\s*"
        r"(?P<min>\d{2,3}(?:,\d{3})+|\d{4,6})"
        r"\s*(?:-|–|—|to)\s*"
        r"(?P<currency2>\$|£|€|C\$|A\$|S\$|NZ\$|₹)?\s*"
        r"(?P<max>\d{2,3}(?:,\d{3})+|\d{4,6})",
        re.IGNORECASE
    )

    for match in currency_pattern.finditer(text):

        currency = match.group("currency")

        minimum = int(
            match.group("min").replace(",", "")
        )

        maximum = int(
            match.group("max").replace(",", "")
        )

        values.append({
            "currency": currency,
            "min": minimum,
            "max": maximum
        })

    # €74.8k - €112.2k
    k_pattern = re.compile(
        r"(?P<currency>\$|£|€|C\$|A\$|S\$|NZ\$|₹)\s*"
        r"(?P<min>\d+(?:\.\d+)?)\s*k"
        r"\s*(?:-|–|—|to)\s*"
        r"(?P<currency2>\$|£|€|C\$|A\$|S\$|NZ\$|₹)?\s*"
        r"(?P<max>\d+(?:\.\d+)?)\s*k",
        re.IGNORECASE
    )

    for match in k_pattern.finditer(text):

        currency = match.group("currency")

        minimum = float(
            match.group("min")
        ) * 1000

        maximum = float(
            match.group("max")
        ) * 1000

        values.append({
            "currency": currency,
            "min": minimum,
            "max": maximum
        })

    return values


def salary_from_text(text):

    values = extract_salary_values(text)

    if not values:
        return None

    result = []

    for item in values:

        result.append(
            f"{item['currency']}"
            f"{item['min']:,.0f}"
            f" - "
            f"{item['currency']}"
            f"{item['max']:,.0f}"
            f" / year"
        )

    return " | ".join(result)


# ============================================================
# SALARY SCORE
# ============================================================

def salary_score(job):

    salary = job.get(
        "salary",
        ""
    )

    text = (
        salary
        + " "
        + job.get("description", "")
    )

    values = extract_salary_values(text)

    if not values:
        return 0

    highest = max(
        item["max"]
        for item in values
    )

    # This is a rough priority score.
    # It is NOT a currency conversion.

    if highest >= 200000:
        return 20

    if highest >= 150000:
        return 18

    if highest >= 120000:
        return 16

    if highest >= 100000:
        return 14

    if highest >= 80000:
        return 12

    if highest >= 60000:
        return 10

    if highest >= 50000:
        return 8

    if highest >= 40000:
        return 6

    if highest >= 30000:
        return 4

    return 2


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

        job_id = item.get("id")

        description = clean_html(
            item.get("content", "")
        )

        salary = salary_from_text(
            description
        )

        # ----------------------------------------------------
        # STRUCTURED PAY TRANSPARENCY
        # ----------------------------------------------------

        if job_id:

            detail_url = (
                "https://boards-api.greenhouse.io/v1/boards/"
                + company
                + "/jobs/"
                + str(job_id)
                + "?pay_transparency=true"
            )

            detail = get_json(
                detail_url
            )

            if detail:

                pay_ranges = detail.get(
                    "pay_input_ranges",
                    []
                )

                structured_salary = (
                    format_greenhouse_salary(
                        pay_ranges
                    )
                )

                if structured_salary:

                    salary = structured_salary

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
            "description": description,
            "salary": salary or "Not listed",
            "source": "Greenhouse"
        })

    return jobs


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

    if not isinstance(data, list):
        return []

    jobs = []

    for item in data:

        categories = item.get(
            "categories",
            {}
        )

        description = clean_html(
            item.get(
                "descriptionPlain",
                ""
            )
        )

        salary = salary_from_text(
            description
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
            "description": description,
            "salary": salary or "Not listed",
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

        description = clean_html(
            item.get(
                "descriptionPlain",
                item.get(
                    "description",
                    ""
                )
            )
        )

        salary = salary_from_text(
            description
        )

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
            "description": description,
            "salary": salary or "Not listed",
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

        description = clean_html(
            item.get(
                "description",
                ""
            )
        )

        salary = (
            item.get("salary")
            or salary_from_text(
                description
            )
        )

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
            "description": description,
            "salary": salary or "Not listed",
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

        description = clean_html(
            item.get(
                "description",
                ""
            )
        )

        salary = salary_from_text(
            description
        )

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
            "description": description,
            "salary": salary or "Not listed",
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

        description = clean_html(
            item.get(
                "jobDescription",
                ""
            )
        )

        salary = (
            item.get("salary")
            or salary_from_text(
                description
            )
        )

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
            "description": description,
            "salary": salary or "Not listed",
            "source": "Jobicy"
        })

    return jobs


# ============================================================
# VISA STATUS
# ============================================================

def visa_status(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    negative = [
        "no visa sponsorship",
        "no sponsorship",
        "not able to sponsor",
        "unable to sponsor",
        "cannot sponsor",
        "will not sponsor",
        "without sponsorship"
    ]

    positive = [
        "visa sponsorship",
        "visa sponsor",
        "sponsorship available",
        "visa support",
        "work visa sponsorship",
        "immigration support",
        "sponsor visa"
    ]

    for keyword in negative:

        if keyword in text:

            job["visa_status"] = (
                "🚫 Sponsorship not available"
            )

            return -8

    for keyword in positive:

        if keyword in text:

            job["visa_status"] = (
                "🛂 Sponsorship mentioned"
            )

            return 12

    job["visa_status"] = (
        "❓ Not confirmed"
    )

    return 0


# ============================================================
# RELOCATION
# ============================================================

def relocation_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    keywords = [
        "relocation package",
        "relocation assistance",
        "relocation support",
        "relocation available"
    ]

    for keyword in keywords:

        if keyword in text:

            job["relocation_status"] = (
                "✈️ Relocation mentioned"
            )

            return 6

    job["relocation_status"] = (
        "❓ Not mentioned"
    )

    return 0


# ============================================================
# LOCATION SCORE
# ============================================================

def location_score(job):

    location = job.get(
        "location",
        ""
    ).lower()

    description = job.get(
        "description",
        ""
    ).lower()

    text = location + " " + description

    score = 0

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
        "new zealand",
        "spain",
        "barcelona",
        "madrid"
    ]

    for place in preferred_locations:

        if place in text:
            score += 2

    if "remote" in text:
        score += 8

    return min(score, 10)


# ============================================================
# ROLE SCORE
# ============================================================

def role_score(job):

    title = job.get(
        "title",
        ""
    ).lower()

    score = 0

    # Exact matches
    exact_roles = {
        "videographer": 38,
        "video editor": 38,
        "video producer": 38,
        "senior video editor": 40,
        "senior video producer": 40,
        "content producer": 34,
        "creative producer": 34,
        "content creator": 32,
        "filmmaker": 32,
        "film editor": 32,
        "video director": 34,
        "content director": 34,
        "motion designer": 32,
        "motion graphics designer": 34
    }

    for role, points in exact_roles.items():

        if role in title:
            score = max(
                score,
                points
            )

    # Supporting roles
    supporting = [
        "motion graphics",
        "post production",
        "post-production",
        "multimedia",
        "social video",
        "brand content",
        "experiential",
        "creative designer"
    ]

    for role in supporting:

        if role in title:
            score = max(
                score,
                26
            )

    return min(
        score,
        40
    )


# ============================================================
# SKILL MATCH
# ============================================================

def skill_score(job):

    text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
    ).lower()

    skills = {
        "premiere pro": 4,
        "adobe premiere": 4,
        "after effects": 4,
        "cinema 4d": 4,
        "houdini": 4,
        "davinci resolve": 4,
        "final cut pro": 3,
        "capcut": 2,
        "cinematography": 3,
        "camera": 2,
        "lighting": 2,
        "video editing": 4,
        "storytelling": 2,
        "production": 3,
        "post production": 4,
        "content production": 3,
        "social media": 2,
        "instagram": 2,
        "youtube": 2,
        "commercial": 2,
        "advertising": 2,
        "brand content": 3,
        "motion design": 4,
        "motion graphics": 4,
        "creative cloud": 2
    }

    score = 0

    for skill, points in skills.items():

        if skill in text:
            score += points

    return min(
        score,
        25
    )


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
        score += 5

    if "lead" in title:
        score += 7

    if "principal" in title:
        score += 7

    if "head" in title:
        score += 8

    if "director" in title:
        score += 8

    if "manager" in title:
        score += 6

    return score


# ============================================================
# EXPERIENCE
# ============================================================

def experience_info(job):

    text = job.get(
        "description",
        ""
    )

    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:relevant\s*)?(?:experience|motion design experience|video experience)",
        r"minimum\s*(?:of\s*)?(\d+)\s*years?",
        r"at least\s*(\d+)\s*years?",
        r"(\d+)\+?\s*years?\s*in"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            years = int(
                match.group(1)
            )

            job["experience_years"] = years

            job["experience_required"] = (
                f"{years}+ years"
            )

            return years

    job["experience_years"] = None

    job["experience_required"] = (
        "Not specified"
    )

    return None


# ============================================================
# EXPERIENCE SCORE
# ============================================================

def experience_score(job):

    years = job.get(
        "experience_years"
    )

    if years is None:
        return 0

    # Don't reward extreme requirements too heavily.
    if years <= 2:
        return 5

    if years <= 3:
        return 4

    if years <= 5:
        return 3

    if years <= 7:
        return 2

    return 1


# ============================================================
# COMPANY / INDUSTRY
# ============================================================

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
        "sports",
        "streaming",
        "studio",
        "experiential"
    ]

    score = 0

    for keyword in keywords:

        if keyword in text:
            score += 1

    return min(
        score,
        8
    )


# ============================================================
# DIRECT EMPLOYER
# ============================================================

def source_score(job):

    if job.get(
        "source"
    ) in [
        "Greenhouse",
        "Lever",
        "Ashby"
    ]:
        return 5

    return 0


# ============================================================
# MATCH REASONS
# ============================================================

def match_reasons(job):

    title = job.get(
        "title",
        ""
    ).lower()

    text = (
        title
        + " "
        + job.get(
            "description",
            ""
        ).lower()
    )

    reasons = []

    if "videographer" in title:
        reasons.append("Videography")

    if "video editor" in title:
        reasons.append("Video Editing")

    if "video producer" in title:
        reasons.append("Video Production")

    if "content producer" in title:
        reasons.append("Content Production")

    if "creative producer" in title:
        reasons.append("Creative Production")

    if "motion" in title:
        reasons.append("Motion Design")

    if "after effects" in text:
        reasons.append("After Effects")

    if "premiere" in text:
        reasons.append("Premiere Pro")

    if "cinema 4d" in text:
        reasons.append("Cinema 4D")

    if "houdini" in text:
        reasons.append("Houdini")

    if "brand content" in text:
        reasons.append("Brand Content")

    if "production" in text:
        reasons.append("Production")

    if "experiential" in text:
        reasons.append("Experiential")

    if job.get(
        "salary",
        "Not listed"
    ) != "Not listed":
        reasons.append("Salary Listed")

    if "remote" in text:
        reasons.append("Remote")

    return reasons[:8]


# ============================================================
# FINAL SCORE
# ============================================================

def score_job(job):

    experience_info(job)

    role = role_score(job)
    skills = skill_score(job)
    salary = salary_score(job)
    location = location_score(job)
    visa = visa_status(job)
    relocation = relocation_score(job)
    seniority = seniority_score(job)
    experience = experience_score(job)
    industry = industry_score(job)
    source = source_score(job)

    total = (
        role
        + skills
        + salary
        + location
        + visa
        + relocation
        + seniority
        + experience
        + industry
        + source
    )

    # Maximum 100
    job["score"] = min(
        total,
        100
    )

    if job["score"] >= 85:
        job["rating"] = "🔥 EXCELLENT"

    elif job["score"] >= 70:
        job["rating"] = "🟢 STRONG"

    elif job["score"] >= 55:
        job["rating"] = "🟡 REVIEW"

    else:
        job["rating"] = "⚪ LOW"

    job["match_reasons"] = match_reasons(
        job
    )

    # Keep score components for debugging
    job["score_breakdown"] = {
        "role": role,
        "skills": skills,
        "salary": salary,
        "location": location,
        "visa": visa,
        "relocation": relocation,
        "seniority": seniority,
        "experience": experience,
        "industry": industry,
        "source": source
    }

    return job["score"]


# ============================================================
# MAIN
# ============================================================

def main():

    print("==========================================")
    print("🌍 INTERNATIONAL JOB HUNTER 6.0")
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

    # --------------------------------------------------------
    # COMPANY BOARDS
    # --------------------------------------------------------

    print("")
    print("🏢 SEARCHING COMPANY CAREER BOARDS")
    print("------------------------------------------")

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

    # --------------------------------------------------------
    # GENERAL BOARDS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FILTER + SCORE
    # --------------------------------------------------------

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

        # Minimum quality threshold
        if job["score"] < 55:
            continue

        filtered.append(
            job
        )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    filtered.sort(
        key=lambda job: (
            job.get("score", 0),
            salary_score(job),
            role_score(job)
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    max_jobs = config.get(
        "max_jobs_per_day",
        10
    )

    # Keep at least 15 available if config is lower
    max_jobs = max(
        int(max_jobs),
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

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "version":
            "6.0",

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

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    for number, job in enumerate(
        filtered,
        1
    ):

        print("")
        print(
            f"🎯 JOB #{number}"
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
            f"💰 Salary: "
            f"{job.get('salary', 'Not listed')}"
        )

        print(
            f"⭐ Match Score: "
            f"{job['score']}/100 "
            f"{job['rating']}"
        )

        print(
            f"🛂 "
            f"{job.get('visa_status', '❓ Not confirmed')}"
        )

        print(
            f"✈️ "
            f"{job.get('relocation_status', '❓ Not mentioned')}"
        )

        print(
            f"🧑‍💼 Experience: "
            f"{job.get('experience_required', 'Not specified')}"
        )

        print(
            "🎯 Why: "
            + ", ".join(
                job.get(
                    "match_reasons",
                    []
                )
            )
        )

        print(
            f"🔎 Source: "
            f"{job['source']}"
        )

        print(
            f"🔗 {job['url']}"
        )

    print("")
    print(
        "=========================================="
    )

    print(
        "✅ JOB SEARCH COMPLETE"
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
