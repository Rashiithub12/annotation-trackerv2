"""AI-powered supplier research engine aligned to the SOP."""
import asyncio
import concurrent.futures
import json
import os
import queue
import re
import threading
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions

# Request queue to serialize concurrent research requests (prevents rate limiting & conflicts)
_work_queue: "queue.Queue[tuple[concurrent.futures.Future, str, list[dict] | None]]" = queue.Queue()
_queue_init_lock = threading.Lock()
_queue_initialized = False


def _init_queue():
    """Initialize the background queue worker."""
    global _queue_initialized
    with _queue_init_lock:
        if not _queue_initialized:
            _queue_initialized = True
            _start_queue_worker()


def _start_queue_worker():
    """Start the background thread that processes queued research requests."""
    def worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_queue_processor())
        except Exception:
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


async def _queue_processor():
    """Process research requests from the queue one at a time."""
    while True:
        future, website_url, existing_companies = await asyncio.to_thread(_work_queue.get)

        try:
            result = await research_company(website_url, existing_companies)
            future.set_result(result)
        except Exception as exc:
            future.set_exception(exc)
        finally:
            _work_queue.task_done()


async def queue_research(website_url: str, existing_companies: list[dict] | None = None) -> dict:
    """Queue a research request and wait for the result (ensures serialized concurrent access)."""
    cf_future = submit_research_request(website_url, existing_companies)
    asyncio_future = asyncio.wrap_future(cf_future)
    return await asyncio_future


def submit_research_request(website_url: str, existing_companies: list[dict] | None = None) -> concurrent.futures.Future:
    """Queue a research request and return a thread-safe future for sync Flask handlers."""
    _init_queue()
    cf_future: concurrent.futures.Future = concurrent.futures.Future()
    _work_queue.put((cf_future, website_url, existing_companies))
    return cf_future


# HTML error signatures that indicate blocked/failed requests
_HTML_ERROR_SIGNATURES = [
    "<html",
    "<!DOCTYPE html",
    "<!DOCTYPE html>",
    "cloudflare",
    "cf-challenge",
    "checking your browser",
    "access denied",
    "403 forbidden",
    "rate limit",
    "too many requests",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
]


def _is_html_error_response(text: str) -> bool:
    """Check if response text looks like an HTML error page rather than valid content."""
    if not text:
        return True
    text_lower = text.strip()[:500].lower()
    return any(sig in text_lower for sig in _HTML_ERROR_SIGNATURES)


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]  # seconds between retries

SOP_CATEGORY_PAIRS = [
    ("10", "Servers"),
    ("11", "Server Options"),
    ("12", "Storage"),
    ("13", "Networking"),
    ("14", "Desktop"),
    ("15", "Notebook"),
    ("16", "Printers and Photocopier"),
    ("17", "Supplies"),
    ("18", "Scanners"),
    ("19", "Surveillance"),
    ("20", "UPS and Power Systems"),
    ("21", "Cables"),
    ("22", "Mobiles and Tablets"),
    ("23", "Software"),
    ("24", "Gaming Products"),
    ("25", "Tech Furniture"),
    ("26", "Synergy"),
    ("32", "Services and Support"),
]

SOP_CATEGORIES = [label for _, label in SOP_CATEGORY_PAIRS]
SOP_CATEGORY_LOOKUP = {label.lower(): (number, label) for number, label in SOP_CATEGORY_PAIRS}

DIRECTORY_SIGNALS = [
    "yellowpages",
    "alibaba",
    "directindustry",
    "elioplus",
    "tradekey",
    "globalsources",
    "indiamart",
    "thomasnet",
    "kompass",
    "iqdirectory",
    "2gis",
    "zawya",
    "tradeindia",
]

GENERIC_EMAIL_PREFIXES = (
    "info@",
    "sales@",
    "contact@",
    "admin@",
    "support@",
    "hello@",
    "orders@",
    "enquiries@",
    "enquiry@",
    "customer.service@",
    "customerservice@",
    "service@",
)

PAGE_KEYWORDS = [
    "contact",
    "contact-us",
    "contactus",
    "about",
    "about-us",
    "support",
    "customer-support",
    "customer-service",
    "help",
    "team",
    "staff",
    "find-us",
    "brands",
    "brand",
    "partners",
    "partner",
    "vendors",
    "vendor",
    "manufacturers",
    "products",
    "solutions",
    "services",
    "distributors",
    "distribution",
]

FACEBOOK_SKIP_TOKENS = [
    "/sharer",
    "/share",
    "/dialog",
    "/plugins/",
    "/events/",
    "/groups/",
    "/watch",
    "/reel/",
]

BRAND_STOPWORDS = {
    "click to know more",
    "show more",
    "home",
    "products",
    "about us",
    "gallery",
    "videos",
    "blog",
    "search",
    "brands",
    "contact",
    "follow us",
    "dubai, uae",
    "featured",
    "on sale",
    "previous",
    "next",
}

CATEGORY_SIGNAL_RULES = [
    ("10 Servers", ["server", "rack server", "blade server", "industrial server"]),
    ("11 Server Options", ["server option", "server accessories", "raid controller", "server memory", "server cpu"]),
    ("12 Storage", ["storage", "nas", "san", "ssd", "hard drive", "data storage"]),
    ("13 Networking", ["network", "communication", "ethernet", "io-link", "router", "switch", "firewall", "wireless access point"]),
    ("14 Desktop", ["desktop", "industrial pc", "panel pc", "computer"]),
    ("15 Notebook", ["notebook", "laptop"]),
    ("16 Printers and Photocopier", ["printer", "photocopier", "multifunction printer", "mfp"]),
    ("17 Supplies", ["toner", "ink", "consumable", "label tape", "printing supplies"]),
    ("18 Scanners", ["scanner", "barcode scanner", "document scanner"]),
    ("19 Surveillance", ["machine vision", "vision camera", "3d camera", "thermal imaging", "lidar", "cctv", "surveillance", "security camera"]),
    ("20 UPS and Power Systems", ["ups", "power supply", "surge protection", "transformer", "battery charger", "inverter", "power distribution"]),
    ("21 Cables", ["cable", "cable gland", "cable trunking", "cable markers", "fiber optic", "connector", "harness"]),
    ("22 Mobiles and Tablets", ["tablet", "mobile device", "smartphone", "handheld terminal"]),
    ("23 Software", ["software", "vision software", "saas", "cloud platform", "license"]),
    ("24 Gaming Products", ["gaming", "esports", "gaming chair", "gaming monitor"]),
    ("25 Tech Furniture", ["furniture", "mount", "stand", "workstation furniture", "rack cabinet"]),
    ("26 Synergy", ["meeting room", "collaboration", "conference solution", "unified workspace"]),
    ("32 Services and Support", ["service", "support", "maintenance", "integration", "installation", "repair"]),
]

EMAIL_PAGE_PRIORITY = [
    "contact-us/contact",
    "contact-us",
    "contact",
    "support",
    "customer-support",
    "customer-service",
    "help",
    "about-us",
    "about",
    "team",
    "staff",
]


def normalize_url(url: str) -> str:
    """Normalize a user-entered URL."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_domain(url: str) -> str:
    """Extract normalized hostname from URL."""
    parsed = urlparse(normalize_url(url))
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def strip_html(html: str) -> str:
    """Convert HTML to readable prompt text."""
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_visual_signals(html: str) -> str:
    """Extract short visible cues such as image alt text, headings, and card labels."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    signals = []
    seen = set()

    def add_signal(value: str):
        cleaned = re.sub(r"\s+", " ", value or "").strip()
        if not cleaned or len(cleaned) < 2 or len(cleaned) > 80:
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        signals.append(cleaned)

    for tag in soup.select("img[alt], img[title]"):
        add_signal(tag.get("alt", ""))
        add_signal(tag.get("title", ""))

    for tag in soup.select("h1, h2, h3, h4, strong, b, a, button, span, div"):
        text = tag.get_text(" ", strip=True)
        if 2 <= len(text) <= 50:
            add_signal(text)
        if len(signals) >= 250:
            break

    return ", ".join(signals[:250])


def find_relevant_links(base_url: str, html: str) -> list[str]:
    """Find useful internal links on the official website."""
    found = []
    seen = set()
    base_domain = extract_domain(base_url)

    for match in re.finditer(r"""href=["']([^"']+)["']""", html, flags=re.I):
        href = match.group(1).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        host = parsed.netloc.lower()
        path = parsed.path.lower()

        if host.startswith("www."):
            host = host[4:]

        if host != base_domain:
            continue

        if any(keyword in path for keyword in PAGE_KEYWORDS):
            candidate = absolute.split("#")[0]
            if candidate not in seen:
                seen.add(candidate)
                found.append(candidate)

    return found[:12]


def normalize_facebook_url(url: str) -> str:
    """Normalize Facebook URLs and remove tracking/query parameters."""
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    return f"{parsed.scheme}://{host}{path}"


def find_facebook_links(base_url: str, html: str) -> list[str]:
    """Find likely official Facebook page URLs linked from the website."""
    found = []
    seen = set()

    for match in re.finditer(r"""href=["']([^"']+)["']""", html, flags=re.I):
        href = match.group(1).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        host = parsed.netloc.lower()
        path = parsed.path.lower()

        if "facebook.com" not in host and "fb.com" not in host:
            continue
        if any(token in path for token in FACEBOOK_SKIP_TOKENS):
            continue

        candidate = normalize_facebook_url(absolute)
        if candidate and candidate not in seen:
            seen.add(candidate)
            found.append(candidate)

    return found[:5]


def score_email_page(url: str) -> int:
    """Higher score means more likely to contain the best contact email."""
    lower = url.lower()
    for index, token in enumerate(EMAIL_PAGE_PRIORITY):
        if token in lower:
            return 100 - index
    return 0


def extract_emails_from_text(text: str) -> list[str]:
    """Extract raw email candidates from page text."""
    if not text:
        return []
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    cleaned = []
    seen = set()
    for email in emails:
        email = email.strip(" .,:;<>[]()").lower()
        if email not in seen:
            seen.add(email)
            cleaned.append(email)
    return cleaned


def decode_cf_email(encoded: str) -> str:
    """Decode Cloudflare email protection values."""
    try:
        key = int(encoded[:2], 16)
        chars = []
        for index in range(2, len(encoded), 2):
            chars.append(chr(int(encoded[index:index + 2], 16) ^ key))
        return "".join(chars)
    except Exception:
        return ""


def extract_emails_from_html(html: str) -> list[str]:
    """Extract emails directly from raw HTML, including mailto and Cloudflare protected emails."""
    if not html:
        return []

    found = []
    seen = set()

    def add(email: str):
        email = email.strip(" .,:;<>[]()\"'").lower()
        if not email or email in seen:
            return
        seen.add(email)
        found.append(email)

    for match in re.findall(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html, flags=re.I):
        add(match)

    for match in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html):
        add(match)

    for encoded in re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html):
        decoded = decode_cf_email(encoded)
        if decoded:
            add(decoded)

    return found


def choose_best_generic_email(candidates: list[dict], website: str) -> tuple[str, str]:
    """Choose the best same-domain generic email and its source URL."""
    preferred_prefixes = ["sales@", "info@", "contact@", "support@", "admin@", "hello@"]
    best = None

    for candidate in candidates:
        email = candidate["email"]
        source_url = candidate["source_url"]
        source_type = candidate.get("source_type", "website")
        if not validate_company_email(email, website):
            continue
        prefix_rank = next((idx for idx, prefix in enumerate(preferred_prefixes) if email.startswith(prefix)), 999)
        source_rank = 0 if source_type == "website" else 1
        page_rank = -score_email_page(source_url)
        sort_key = (source_rank, prefix_rank, page_rank, len(email))
        if best is None or sort_key < best[0]:
            best = (sort_key, email, source_url)

    if best:
        return best[1], best[2]
    return "-", ""


def extract_brands_from_rendered_page(page: dict) -> list[str]:
    """Extract visible brand names from a rendered brands/partners page."""
    text_sources = [page.get("visual_signals", ""), page.get("text", "")]
    brands = []
    seen = set()

    def add_brand(name: str):
        cleaned = re.sub(r"\s+", " ", name).strip(" -,:;")
        if not cleaned:
            return
        lowered = cleaned.lower()
        if lowered in BRAND_STOPWORDS:
            return
        if len(cleaned) < 2 or len(cleaned) > 40:
            return
        if any(ch.isdigit() for ch in cleaned) and cleaned.count(" ") > 2:
            return
        if lowered in seen:
            return
        seen.add(lowered)
        brands.append(cleaned)

    patterns = [
        r"([A-Za-z0-9&+().,'/\- ]{2,40})\s+Click to Know More",
        r"([A-Za-z0-9&+().,'/\- ]{2,40})\s+Show More",
    ]

    for source in text_sources:
        for pattern in patterns:
            for match in re.findall(pattern, source, flags=re.I):
                add_brand(match)

    return brands[:10]


async def fetch_page_with_retry(client: httpx.AsyncClient, url: str, retries: int = MAX_RETRIES) -> dict:
    """Fetch a page with retry logic and HTML error detection."""
    last_error = None

    for attempt in range(retries):
        try:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            response.raise_for_status()
            html = response.text

            # Detect HTML error responses (Cloudflare, rate limits, etc.)
            if _is_html_error_response(html) and attempt < retries - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                last_error = f"HTML error page detected for {url}, retrying in {delay}s..."
                await asyncio.sleep(delay)
                continue

            return {
                "url": str(response.url),
                "status": response.status_code,
                "html": html,
                "text": strip_html(html)[:12000],
            }
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                await asyncio.sleep(delay)
            continue

    return {
        "url": url,
        "status": "error",
        "html": "",
        "text": f"Error fetching {url} after {retries} attempts: {last_error}",
    }


def fetch_page(client: httpx.AsyncClient, url: str) -> dict:
    """Fetch a page and return metadata plus cleaned text (wrapper for backwards compatibility)."""
    return {
        "url": url,
        "status": "error",
        "html": "",
        "text": f"fetch_page is deprecated, use fetch_page_with_retry for {url}",
    }


def fetch_rendered_page(url: str) -> dict:
    """Render a page with headless Edge so JS-loaded brand grids are visible."""
    cache_dir = Path(__file__).resolve().parent.parent / ".selenium"
    cache_dir.mkdir(exist_ok=True)
    os.environ.setdefault("SE_CACHE_PATH", str(cache_dir))

    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,2600")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = None
    try:
        driver = webdriver.Edge(options=options)
        driver.get(url)
        driver.implicitly_wait(6)
        html = driver.page_source
        return {
            "url": driver.current_url,
            "status": "rendered",
            "html": html,
            "text": strip_html(html)[:12000],
            "visual_signals": extract_visual_signals(html)[:12000],
        }
    except Exception as exc:
        return {
            "url": url,
            "status": "render-error",
            "html": "",
            "text": f"Render error for {url}: {exc}",
            "visual_signals": "",
        }
    finally:
        if driver is not None:
            driver.quit()


def validate_company_email(email: str, website: str) -> bool:
    """Validate that a generic email belongs to the company site."""
    if not email or email == "-":
        return True
    email = email.strip().lower()
    if not any(email.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES):
        return False
    match = re.search(r"@([^@\s]+\.[^@\s]+)$", email)
    if not match:
        return False

    email_domain = match.group(1).lower()
    site_domain = extract_domain(website)
    return (
        email_domain == site_domain
        or email_domain.endswith("." + site_domain)
        or site_domain.endswith("." + email_domain)
    )


def normalize_categories(raw_value: str) -> str:
    """Normalize categories to number + label format."""
    if not raw_value:
        return ""

    wanted = [item.strip() for item in re.split(r"[,;\n]+", raw_value) if item.strip()]
    result = []
    for item in wanted:
        cleaned = re.sub(r"^\d+\s*", "", item).strip().lower()
        if cleaned in SOP_CATEGORY_LOOKUP:
            number, label = SOP_CATEGORY_LOOKUP[cleaned]
            rendered = f"{number} {label}"
            if rendered not in result:
                result.append(rendered)
    return ", ".join(result)


def infer_categories_from_content(text: str) -> str:
    """Infer the closest valid categories from company website content."""
    if not text:
        return ""

    lower = text.lower()
    matches = []
    for rendered, keywords in CATEGORY_SIGNAL_RULES:
        hit_count = sum(1 for keyword in keywords if keyword in lower)
        if hit_count:
            matches.append((rendered, hit_count))

    # Keep categories with the strongest direct evidence first.
    matches.sort(key=lambda item: (-item[1], item[0]))
    return ", ".join(category for category, _ in matches[:6])


def dedupe_flag(company_name: str, website: str, existing_companies: list[dict]) -> str:
    """Flag duplicates conservatively using existing rows."""
    current_domain = extract_domain(website)
    current_name = re.sub(r"\([^)]*\)", "", (company_name or "").lower())
    current_name = re.sub(r"[^a-z0-9]+", " ", current_name).strip()

    for existing in existing_companies:
        existing_domain = extract_domain(existing.get("website", ""))
        existing_name = re.sub(r"\([^)]*\)", "", existing.get("company_name", "").lower())
        existing_name = re.sub(r"[^a-z0-9]+", " ", existing_name).strip()
        if current_domain and existing_domain and current_domain == existing_domain:
            return "Yes"
        if current_name and existing_name and current_name == existing_name:
            return "Yes"
    return "No"


def deterministic_marketplace(website: str) -> str:
    """Deterministic marketplace flag for obvious directory domains."""
    website = website.lower()
    return "Yes" if any(signal in website for signal in DIRECTORY_SIGNALS) else "No"


async def research_company(website_url: str, existing_companies: list[dict] | None = None) -> dict:
    """Research a supplier website and return SOP-aligned structured data."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured. Please set it in .env file."}

    existing_companies = existing_companies or []
    client = Anthropic(api_key=api_key)
    website_url = normalize_url(website_url)

    async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as http_client:
        homepage = await fetch_page_with_retry(http_client, website_url)
        discovered_links = find_relevant_links(homepage["url"], homepage["html"])
        facebook_links = find_facebook_links(homepage["url"], homepage["html"])
        seed_links = [
            homepage["url"],
            urljoin(website_url, "/contact"),
            urljoin(website_url, "/contact/"),
            urljoin(website_url, "/contact-us"),
            urljoin(website_url, "/contact-us/"),
            urljoin(website_url, "/about"),
            urljoin(website_url, "/about/"),
            urljoin(website_url, "/about-us"),
            urljoin(website_url, "/about-us/"),
            urljoin(website_url, "/brands"),
            urljoin(website_url, "/brands/"),
            urljoin(website_url, "/partners"),
            urljoin(website_url, "/partners/"),
            urljoin(website_url, "/distributors"),
            urljoin(website_url, "/distributors/"),
        ]

        ordered_urls = []
        for url in seed_links + discovered_links:
            clean = normalize_url(url)
            if clean and clean not in ordered_urls:
                ordered_urls.append(clean)

        ordered_urls.sort(key=score_email_page, reverse=True)

        pages = await asyncio.gather(
            *[fetch_page_with_retry(http_client, url) for url in ordered_urls[:20]],
            return_exceptions=False,
        )

    rendered_targets = []
    for page in pages:
        if score_email_page(page["url"]) > 0:
            rendered_targets.append(page["url"])
    for page in pages:
        lower_url = page["url"].lower()
        if any(keyword in lower_url for keyword in ["brand", "partner", "vendor", "manufacturer", "product", "distributor"]):
            rendered_targets.append(page["url"])
    if homepage["url"] not in rendered_targets:
        rendered_targets.insert(0, homepage["url"])
    rendered_targets = list(dict.fromkeys(rendered_targets))[:5]

    rendered_pages = []
    for target in rendered_targets:
        rendered_pages.append(await asyncio.to_thread(fetch_rendered_page, target))

    email_candidates = []
    for page in pages + rendered_pages:
        page_text = " ".join([page.get("text", ""), page.get("visual_signals", "")])
        raw_html = page.get("html", "")
        all_emails = extract_emails_from_html(raw_html) + extract_emails_from_text(page_text)
        for email in all_emails:
            email_candidates.append({"email": email, "source_url": page["url"], "source_type": "website"})

    deterministic_email, deterministic_email_source = choose_best_generic_email(email_candidates, website_url)

    facebook_pages = []
    if deterministic_email == "-" and facebook_links:
        for facebook_url in facebook_links[:3]:
            facebook_pages.append(await asyncio.to_thread(fetch_rendered_page, facebook_url))

        facebook_candidates = []
        for page in facebook_pages:
            page_text = " ".join([page.get("text", ""), page.get("visual_signals", "")])
            raw_html = page.get("html", "")
            all_emails = extract_emails_from_html(raw_html) + extract_emails_from_text(page_text)
            for email in all_emails:
                facebook_candidates.append({"email": email, "source_url": page["url"], "source_type": "facebook"})

        deterministic_email, deterministic_email_source = choose_best_generic_email(facebook_candidates, website_url)

    combined_content = "\n\n".join(
        f"=== URL: {page['url']} | STATUS: {page['status']} ===\n{page['text']}"
        for page in pages
    )
    rendered_content = "\n\n".join(
        f"=== RENDERED URL: {page['url']} | STATUS: {page['status']} ===\nTEXT:\n{page['text']}\nVISUAL SIGNALS:\n{page.get('visual_signals', '')}"
        for page in rendered_pages
    )

    deterministic_brands = []
    deterministic_brand_source = ""
    for page in rendered_pages:
        if any(keyword in page["url"].lower() for keyword in ["brands/", "partners/", "vendors/", "manufacturers/"]):
            extracted = extract_brands_from_rendered_page(page)
            if len(extracted) >= len(deterministic_brands):
                deterministic_brands = extracted
                deterministic_brand_source = page["url"]

    prompt = f"""You are a senior supplier research analyst following a strict SOP.

Research this company website and return exactly the required supplier data.

STRICT RULES:

1. WEBSITE
- Use the official company website only.
- If the provided URL itself is a directory or marketplace, keep that URL and set marketplace to "Yes".

2. GENERIC EMAIL
- Email must belong to the company's own domain only.
- Allowed generic emails: info@, sales@, contact@, admin@, support@, hello@
- Never use personal emails.
- Never use parent-company emails unless the website clearly belongs to the same company/domain.
- If no valid email is on the website, check any official Facebook page linked from the website.
- If still not found, return "-"

3. BRANDS / PRODUCTS
- For distributors: list all distributed brands found on brands / partners / vendors / manufacturers pages.
- For manufacturers: list their own products, sub-brands, and subsidiaries.
- Return up to 10 brands maximum.
- Only list brands or product lines that are explicitly visible in the provided website content.
- Do not guess, infer, autocomplete, or add sample series names that are not clearly present in the content.
- Prefer visible brand names from brand cards, partner pages, logo grids, manufacturer pages, and product pages on the official website.
- Return comma-separated text only.

4. SOURCE URLS
- email_source_url must be the exact page where the email was found.
- brands_source_url must be the exact page where brands/products were found.
- Prefer official company pages.

5. CATEGORIES
- Do deep research on the company website and map only to the closest valid categories.
- Many industrial automation suppliers are not broad IT companies, so do not over-tag them.
- Use the closest overlap from the approved list only.
- Return only categories strongly supported by the site content.
- Use only these exact categories and return them in number + label format, comma-separated:
  {", ".join(f"{number} {label}" for number, label in SOP_CATEGORY_PAIRS)}

6. DUPLICATE
- "Yes" only if this company already appears in the existing database list below.
- Same company across locations can still be duplicate.
- Similar-sounding companies with different domains are not duplicates.

7. MARKETPLACE
- "Yes" only if the site is a directory or true marketplace/intermediary.
- Retailers are not marketplaces.

Existing database list:
{json.dumps(existing_companies[:300], ensure_ascii=True)}

Website content:
{combined_content[:70000]}

Rendered browser content for visible brand/logo sections:
{rendered_content[:40000]}

Return JSON only in this exact shape:
{{
  "company_name": "",
  "website": "{website_url}",
  "generic_email": "",
  "brands": "",
  "email_source_url": "",
  "brands_source_url": "",
  "brand_categories": "",
  "duplicate": "Yes/No",
  "marketplace": "Yes/No",
  "notes": ""
}}
"""

    try:
        message = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract text from content blocks, skipping thinking blocks
        text_parts = []
        for block in message.content:
            # ThinkingBlock uses 'thinking' attribute, TextBlock uses 'text'
            # Safely get the text attribute, default to empty string
            block_text = getattr(block, "text", "") or ""
            if block_text:
                text_parts.append(block_text)
        response_text = " ".join(text_parts).strip()

        # Detect HTML error pages (Cloudflare, rate limits, etc.) from AI API
        if _is_html_error_response(response_text):
            return {"error": f"AI API returned an error page (likely rate limit or cloudflare challenge). Please wait a moment and try again."}

        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not json_match:
            return {"error": f"AI response did not contain valid JSON structure: {response_text[:200]}"}
        result = json.loads(json_match.group())
    except json.JSONDecodeError as exc:
        return {"error": f"Failed to parse AI response: {exc}"}
    except Exception as exc:
        return {"error": f"AI research failed: {exc}"}

    result["website"] = website_url
    inferred_categories = infer_categories_from_content(
        " ".join([combined_content, rendered_content, result.get("brands", ""), result.get("notes", "")])
    )
    normalized_ai_categories = normalize_categories(result.get("brand_categories", ""))
    result["brand_categories"] = inferred_categories or normalized_ai_categories
    result["duplicate"] = dedupe_flag(result.get("company_name", ""), website_url, existing_companies)

    if deterministic_marketplace(website_url) == "Yes":
        result["marketplace"] = "Yes"
    else:
        result["marketplace"] = "Yes" if result.get("marketplace") == "Yes" else "No"

    if deterministic_email != "-":
        result["generic_email"] = deterministic_email
        result["email_source_url"] = deterministic_email_source

    if deterministic_brands:
        result["brands"] = ", ".join(deterministic_brands[:10])
        if deterministic_brand_source:
            result["brands_source_url"] = deterministic_brand_source

    if not validate_company_email(result.get("generic_email", ""), website_url):
        notes = result.get("notes", "").strip()
        result["notes"] = f"{notes} Generic email did not match company domain and was reset.".strip()
        result["generic_email"] = "-"
        if deterministic_email != "-":
            result["generic_email"] = deterministic_email
            result["email_source_url"] = deterministic_email_source

    for key in [
        "company_name",
        "website",
        "generic_email",
        "brands",
        "email_source_url",
        "brands_source_url",
        "brand_categories",
        "duplicate",
        "marketplace",
        "notes",
    ]:
        result[key] = str(result.get(key, "") or "").strip()

    if result["duplicate"] not in {"Yes", "No"}:
        result["duplicate"] = "No"
    if result["marketplace"] not in {"Yes", "No"}:
        result["marketplace"] = "No"

    return result
