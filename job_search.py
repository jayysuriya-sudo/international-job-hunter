import json
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
                "User-Agent": "Mozilla/5.0 InternationalJobHunter/5.0",
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
# HTML CLEANING
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


# ==================================================
# ROLE KEYWORDS
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
    "digital content producer",
    "experiential designer",
    "creative designer"
]


def matches_title(title):

    title = title.lower()

    return any(
        keyword in title
        for keyword in PRIMARY_ROLES + SECONDARY_ROLES
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

    # First get the normal job list
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
            item.get(
                "content",
                ""
            )
        )

        salary = extract_salary_from_text(
            description
        )

        # ------------------------------------------
        # Get structured Greenhouse pay data
        # ------------------------------------------

        if job_id:

            detail_url = (
                "https://boards-api.greenhouse.io/v1/"
                "boards/"
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

                structured_salary = format_greenhouse_salary(
                    pay_ranges
                )

                if structured_salary:

                    salary = structured_salary

                    # Add salary information to description
                    description += (
                        " "
                        + structured_salary
                    )

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
            "salary": salary,
            "source": "Greenhouse"
        })

    return jobs


# ==================================================
# GREENHOUSE STRUCTURED SALARY
# ==================================================

def format_greenhouse_salary(pay_ranges):

    if not pay_ranges:
        return None

    results = []

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

        if minimum is None or maximum is None:
            continue

        minimum = minimum / 100
        maximum = maximum / 100

        symbol = {
            "USD": "$",
            "CAD": "C$",
            "AUD": "A$",
            "GBP": "£",
            "EUR": "€",
            "SGD": "S$",
            "NZD": "NZ$"
        }.get(
            currency,
            currency + " "
        )

        results.append(
            f"{symbol}{minimum:,.0f} - "
            f"{symbol}{maximum:,.0f} / year"
        )

    if results:
        return " | ".join(results)

    return None


# ==================================================
# SALARY FROM TEXT
# ==================================================

def extract_salary_from_text(text):

    if not text:
        return "Not listed"

    patterns = [

        r"\$[\d,]+(?:\s*-\s*\$?[\d,]+)?",

        r"£[\d,]+(?:\s*-\s*£?[\d,]+)?",

        r"€[\d,]+(?:\s*-\s*€?[\d,]+)?",

        r"C\$[\d,]+(?:\s*-\s*C\$?[\d,]+)?",

        r"A\$[\d,]+(?:\s*-\s*A\$?[\d,]+)?",

        r"\b\d{2,3}k(?:\s*-\s*\d{2,3}k)?"

    ]

    matches = []

    for pattern in patterns:

        found = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        matches.extend(
            found
        )

    if matches:

        return matches[0]

    return "Not listed"


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

        description = clean_html(
            item.get(
                "descriptionPlain",
                ""
            )
        )

        salary = extract_salary_from_text(
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
            "salary": salary,
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

        description = clean_html(
            item.get(
                "descriptionPlain",
                item.get(
                    "description",
                    ""
                )
            )
        )

        salary = extract_salary_from_text(
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
            "salary": salary,
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

        description = clean_html(
            item.get(
                "description",
                ""
            )
        )

        salary = (
            item.get(
                "salary"
            )
            or extract_salary_from_text(
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
            "salary": salary,
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

        description = clean_html(
            item.get(
                "description",
                ""
            )
        )

        salary = extract_salary_from_text(
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
            "salary": salary,
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

        description = clean_html(
            item.get(
                "jobDescription",
                ""
            )
        )

        salary = (
            item.get(
                "salary",
                ""
            )
            or extract_salary_from_text(
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
            "salary": salary,
            "source": "Jobicy"
        })

    return jobs


# ==================================================
# SALARY SCORE
# ==================================================

def salary_score(job):

    salary = job.get(
        "salary",
        ""
    )

    text = (
        salary
        + " "
        + job.get(
            "description",
            ""
        )
    )

    text = text.replace(
        ",",
        ""
    )

    # Extract monetary values
    matches = re.findall(
        r"(?:\$|£|€|C\$|A\$|S\$|NZ\$)?\s?"
        r"(\d{2,3})(?:000|,000|k\b)",
        text,
        re.IGNORECASE
    )

    values = []

    for value in matches:

        try:

            number = int(
                value
            ) * 1000

            values.append(
                number
            )

        except ValueError:
            pass

    # Also detect full numbers
    full_numbers = re.findall(
        r"(?:\$|£|€|C\$|A\$|S\$|NZ\$)"
        r"\s?(\d{5,6})",
        text
    )

    for value in full_numbers:

        try:
            values.append(
                int(value)
            )
        except ValueError:
            pass

    if not values:

        return 0

    highest = max(
        values
    )

    if highest >= 200000:
        return 40

    if highest >= 150000:
        return 38

    if highest >= 120000:
        return 35

    if highest >= 100000:
        return 32

    if highest >= 80000:
        return 28

    if highest >= 70000:
        return 25

    if highest >= 60000:
        return 22

    if highest >= 50000:
        return 18

    if highest >= 40000:
        return 12

    if highest >= 30000:
        return 7

    return 3


# ==================================================
# VISA SCORE
# ==================================================

def visa_status(job):

    text = (
        job.get(
            "title",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
    ).lower()

    positive = [
        "visa sponsorship",
        "visa sponsor",
        "sponsorship available",
        "visa support",
        "work visa sponsorship",
        "immigration support",
        "sponsor visa"
    ]

    negative = [
        "no sponsorship",
        "without sponsorship",
        "unable to sponsor",
        "will not sponsor",
        "cannot sponsor"
    ]

    for keyword in negative:

        if keyword in text:

            job["visa_status"] = (
                "🚫 Sponsorship not available"
            )

            return 0

    for keyword in positive:

        if keyword in text:

            job["visa_status"] = (
                "🛂 Sponsorship mentioned"
            )

            return 20

    job["visa_status"] = (
        "❓ Not confirmed"
    )

    return 0


# ==================================================
# RELOCATION
# ==================================================

def relocation_score(job):

    text = (
        job.get(
            "title",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
    ).lower()

    keywords = [
        "relocation package",
        "relocation assistance",
        "relocation support",
        "relocation available",
        "relocation"
    ]

    for keyword in keywords:

        if keyword in text:

            job["relocation_status"] = (
                "✈️ Relocation mentioned"
            )

            return 10

    job["relocation_status"] = (
        "❓ Not mentioned"
    )

    return 0


# ==================================================
# LOCATION
# ==================================================

def location_score(job):

    text = (
        job.get(
            "location",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
    ).lower()

    preferred = [
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

    for location in preferred:

        if location in text:
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
        score += 12

    if "lead" in title:
        score += 15

    if "principal" in title:
        score += 15

    if "head" in title:
        score += 18

    if "manager" in title:
        score += 15

    if "director" in title:
        score += 18

    return score


# ==================================================
# ROLE SCORE
# ==================================================

def role_score(job):

    title = job.get(
        "title",
        ""
    ).lower()

    score = 0

    highest_priority = [
        "video editor",
        "videographer",
        "video producer"
    ]

    strong_roles = [
        "content producer",
        "creative producer",
        "content creator",
        "filmmaker",
        "film editor",
        "motion designer"
    ]

    supporting_roles = [
        "motion graphics",
        "post production",
        "multimedia",
        "social video",
        "brand content",
        "experiential"
    ]

    for role in highest_priority:

        if role in title:
            score += 35

    for role in strong_roles:

        if role in title:
            score += 28

    for role in supporting_roles:

        if role in title:
            score += 22

    return min(
        score,
        40
    )


# ==================================================
# SKILLS
# ==================================================

def skill_score(job):

    text = (
        job.get(
            "title",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
    ).lower()

    skills = [
        "premiere pro",
        "adobe premiere",
        "after effects",
        "cinema 4d",
        "houdini",
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
        "brand content",
        "motion design",
        "motion graphics"
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
# INDUSTRY
# ==================================================

def industry_score(job):

    text = (
        job.get(
            "title",
            ""
        )
        + " "
        + job.get(
            "description",
            ""
        )
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
        "experiential"
    ]

    score = 0

    for industry in industries:

        if industry in text:
            score += 2

    return min(
        score,
        15
    )


# ==================================================
# DIRECT EMPLOYER
# ==================================================

def source_score(job):

    if job.get(
        "source"
    ) in [
        "Greenhouse",
        "Lever",
        "Ashby"
    ]:

        return 8

    return 0


# ==================================================
# EXPERIENCE
# ==================================================

def experience_info(job):

    text = (
        job.get(
            "description",
            ""
        )
    )

    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:relevant\s*)?(?:experience|motion design experience|video experience)",
        r"minimum\s*(?:of\s*)?(\d+)\s*years?",
        r"at least\s*(\d+)\s*years?"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            years = match.group(
                1
            )

            job["experience_required"] = (
                f"{years}+ years"
            )

            return

    job["experience_required"] = (
        "Not specified"
    )


# ==================================================
# WHY MATCH
# ==================================================

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
        )
    ).lower()

    reasons = []

    if "video editor" in title:
        reasons.append(
            "Video Editing"
        )

    if "videographer" in title:
        reasons.append(
            "Videography"
        )

    if "video producer" in title:
        reasons.append(
            "Video Production"
        )

    if "motion" in title:
        reasons.append(
            "Motion Design"
        )

    if "content" in title:
        reasons.append(
            "Content Creation"
        )

    if "producer" in title:
        reasons.append(
            "Creative Production"
        )

    if "after effects" in text:
        reasons.append(
            "After Effects"
        )

    if "premiere" in text:
        reasons.append(
            "Premiere Pro"
        )

    if "cinema 4d" in text:
        reasons.append(
            "Cinema 4D"
        )

    if "brand" in text:
        reasons.append(
            "Brand Content"
        )

    if "production" in text:
        reasons.append(
            "Production"
        )

    if "advertising" in text:
        reasons.append(
            "Advertising"
        )

    if "experiential" in text:
        reasons.append(
            "Experiential"
        )

    if job.get(
        "salary",
        "Not listed"
    ) != "Not listed":

        reasons.append(
            "Salary Listed"
        )

    return reasons[:8]


# ==================================================
# FINAL SCORE
# ==================================================

def score_job(job):

    score = 0

    score += role_score(
        job
    )

    score += salary_score(
        job
    )

    score += location_score(
        job
    )

    score += visa_status(
        job
    )

    score += relocation_score(
        job
    )

    score += seniority_score(
        job
    )

    score += skill_score(
        job
    )

    score += industry_score(
        job
    )

    score += source_score(
        job
    )

    # Maximum displayed score
    job["score"] = min(
        score,
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
        match_reasons(
            job
        )
    )

    experience_info(
        job
    )

    return job["score"]


# ==================================================
# MAIN
# ==================================================

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

    # ------------------------------------------
    # COMPANY BOARDS
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
    # GENERAL SOURCES
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

        score_job(
            job
        )

        if job["score"] < 60:
            continue

        filtered.append(
            job
        )

    # ------------------------------------------
    # DEDUPLICATE
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
        key=lambda job: (
            job["score"],
            salary_score(job)
        ),
        reverse=True
    )

    # ------------------------------------------
    # TOP 15
    # ------------------------------------------

    max_jobs = max(
        config.get(
            "max_jobs_per_day",
            10
        ),
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
    # SAVE
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
    # LOG RESULTS
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
            f"🎯 Why: "
            f"{', '.join(job.get('match_reasons', []))}"
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
