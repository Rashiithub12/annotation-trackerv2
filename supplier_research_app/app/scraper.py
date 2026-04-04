"""
Brand/Partner Scraper - Local scraper without external APIs.

Extracts brands, partners, vendors from company websites.
"""

import cloudscraper
import re
import ssl
import urllib.request
from typing import Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# Settings
FAST_TIMEOUT = 5
MAX_BRAND_PAGES = 5

NOISE_PATTERNS = [
    r"^logo$", r"^phone$", r"^email$", r"^address$", r"^copyright",
    r"^all rights reserved", r"^privacy", r"^terms", r"^cookies?",
    r"^menu$", r"^home$", r"^contact", r"^about", r"^login$",
    r"^sign in$", r"^search$", r"^buy$", r"^shop$", r"^cart$",
    r"^checkout$", r"^icon$", r"^button$", r"^link$",
    r"cyber", r"security", r"service", r"solution", r"trust",
    r"support", r"management", r"advisory", r"consulting", r"^outsourcing$",
    r"^footer$", r"^header$", r"^nav$", r"^wrapper$", r"^container$",
    r"^copyright", r"^all rights", r"^privacy policy",
    r"printing", r"printer", r"office ", r" dubai", r"uae",
    r"\.png", r"\.jpg", r"\.jpeg", r"\.svg", r"\.gif", r"\.webp",
    r"\bpng\b", r"\bjpg\b", r"\bjpeg\b", r"\bsvg\b", r"\bgif\b", r"\bwebp\b",
    r"untitled", r"unitled",
    r"\d{10,}[a-zA-Z0-9]+", r"[a-zA-Z0-9]+\d{10,}",
    r"^[a-z]+-[a-z]+-[a-z]+-[a-z]+-", r"^[a-z]+-[a-z]+-[a-z]+-",
    r"^[a-z]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-", r"^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-",
    r"^tr$", r"^fpv$", r"^klarna$", r"^emlid$",
    r"for sale", r"easy returns", r"price match", r"free next day",
    r"click & collect", r"paypal", r"clearpay", r"dragon", r"den ",
    r"weekends?", r"mon-sat", r"mon-fri", r"open ",
    r"questions", r"information", r"password", r"forgot",
    r"the largest", r"the best", r"highest rated", r"ship 7 days",
    r"part of", r"register", r"retailer", r"accessories", r"cameras",
    r"^dji retailer$",
    r"memory cards for drones", r"drone luts", r"sub 250g drones",
    r"enterprise drones", r"online courses", r"^others$", r"clearance hangar",
    r"repair & servicing", r"^dji drones$",
    r"prebuilt fpv drones", r"fpv drones", r"fpv batteries", r"fpv chargers",
    r"^software$", r"drone safe store",
    r"paypal", r"clearpay", r"visa", r"mastercard", r"amex",
    r"apple pay", r"pay by amazon", r"klarna",
    r"master card", r"uk tax payer", r"cash back",
    r"laser printers", r"inkjet printers", r"multifunction printers",
    r"a3 printers", r"ink tank printers", r"ecotank",
    r"expert advice", r"printer experts", r"printer paper",
    r"multifunction", r"ink tank", r"laser printers", r"inkjet printers",
    r"partner logo", r"approved logo", r"logo",
    r"free next day", r"same day dispatch", r"free delivery",
    r"rfid solutions", r"barcode scanners", r"barcode and label",
    r"labels and ribbons", r"mobile computers", r"id card printers",
    r"rfid equipment", r"epos systems", r"access control",
    r"barcode warehouse", r"barcode and label printers",
    r"professional services", r"managed services", r"technical support",
    r"repairs & servicing", r"leasing & rentals",
    r"android enterprise", r"gs1 approved", r"accepted cards",
    r"peoplevox", r"descartes",
    r"gold partner", r"silver partner", r"bronze partner",
    r"advanced partner", r"certified partner", r"authorized partner",
    r"registered partner", r"select partner", r"premier partner",
    r"enterprise partner", r"global partner",
    r"man speaking", r"warehouse worker", r"smiling",
    r"voyager", r"zd421", r"tc22", r"tm-m30",
    r"z-perform", r"zebra 2300", r"vb00",
    r"\d{3,}[a-z]",
    r"^rfid$", r"^barcode$", r"labels and", r"^id card$",
    r"^epos$", r"^managed$", r"^professional$",
    r"falcona", r"staylinked", r"worx",
    r"^elo$", r"elo touch",
    r"retailer of the year", r"best online retailer", r"award winner",
    r"shop by category", r"buy now", r"add to cart", r"in stock",
    r"free delivery", r"price match", r"easy returns",
    r"ecosys", r"versalink", r"officejet", r"ink tank",
    r"tax payer", r"cash back",
    r"mini [0-9]", r"mavic", r"matrice", r"avata", r"fpv",
    r"ronin", r"osmo", r"phantom", r"tello", r"inspire [0-9]",
    r"terra", r"power", r"care refresh",
    r"dji neo", r"dji flip", r"dji air 3", r"dji rs 3", r"dji mic mini",
    r"dji mic$", r"dji mic ",
    r"insta360 x[0-9]", r"insta360 go [0-9]", r"insta360 one",
    r"here to help", r"special offers", r"trade-in offer",
    r"free no-obligation", r"hassle free", r"no obligation",
    r"free no-oblig",
    r"^trade$", r"^finance$", r"^leasing$",
    r"^asset leasing$", r"^solar leasing$",
    r"strong ship commitment", r"product customer", r"incentive rewards",
    r"check mark", r"commitment", r"incentive", r"rewards",
    r"^navigation$", r"buying from us", r"your cloud",
    r"gdp?r? policy", r"modern slavery", r"carbon reduction",
    r"strategic business", r"olark", r"live chat",
    r"contact us", r"about us", r"about us", r"our services",
    r"^home$", r"^services$", r"^solutions$", r"^products$",
    r"government", r"^department", r"council", r"college", r"chamber",
    r"public sector", r"authority", r"nhs", r"nhs trust",
    r"youtube", r"facebook", r"twitter", r"linkedin", r"instagram",
    r"tiktok", r"snapchat", r"pinterest", r"reddit", r"xing",
    r"^youtube$", r"^facebook$", r"^twitter$", r"^linkedin$", r"^instagram$",
    r"cover image", r"blog banner", r"threat advisory", r"ot security",
    r"cover$", r"banner$",
    r"^[0-9]+_[a-zA-Z0-9_]{20,}$",
]

NOISE_EXACT = {
    "home", "about", "contact", "products", "services", "solutions", "login",
    "sign in", "privacy", "terms", "cookies", "careers", "blog", "news",
    "support", "copyright", "all rights reserved", "menu", "search",
    "cart", "checkout", "icon", "button", "link",
    "cloud computing", "computer infrastructure", "it procurement", "public sector",
    "click to", "read more", "learn more", "view all", "show more",
    "en_us", "en-gb", "admin", "console",
    "screenshot", "admin console", "value incentive", "value incentive plan",
    "what we do", "expertise", "applications", "integrations", "devices",
    "it modernization", "methodology", "industries", "featured content",
    "client stories", "by topic", "explore", "our client stories",
    "government drives roi", "content & resources", "data & ai",
    "implementation", "devshop", "prism", "radius",
    "shop buy", "close-up", "government facility", "featured content",
    "svg", "svg%", "banner", "slider", "mobile", "desktop", "tablet",
    "hero", "footer", "header", "nav", "navbar", "sidebar", "wrapper",
    "container", "content", "main", "section", "row", "col",
    "jpg", "jpeg", "png", "webp", "gif", "avif", "ico",
    "thumb", "thumbnail", "background", "hover", "active", "disabled",
    "ellp", "frame", "tab", "panel", "accordion", "modal", "dropdown",
    "framework", "manifesto", "optimization", "numbers",
    "cybersecurity", "cyber security", "security services", "managed security",
    "professional services", "project management", "cloud security", "endpoint security",
    "network security", "application security", "data security", "ot security",
    "iot security", "malware analysis", "threat exposure", "cyber trust",
    "offensive cybersecurity", "identity fabric", "privacy", "compliance",
    "vulnerability advisory", "threat advisory", "whitepaper", "case study",
    "customer insight", "our story", "mission", "vision", "principles",
    "leadership", "resources", "media", "video", "blog", "event",
    "trust center", "partner program", "why join us", "join our talent",
    "awards", "legal", "speak up", "sponsorships", "training", "certifications",
    "revenue model", "collaboration", "engagement", "comprehensive",
    "logo footer", "logo", "skip to content", "next arrow",
    "innovation realm", "public key infrastructure pki", "secops", "identity fabric immunity",
    "securing ai", "post quantum", "hyperscalers", "zero trust",
    "e2e zero trust", "securing your digital journey", "resilient adaptive cyber defense",
    "end to end", "supply chain", "operational technology", "ot",
    "mission & vision", "blog post", "videos", "threat advisories",
    "reports & whitepapers", "case studies", "customer insight story",
    "events", "join our talent community", "secure access edge", "sase",
    "sort by", "our story", "principles leadership", "share via",
    "company", "our network", "case studies customer",
    "innovation", "realm", "secure", "digital", "journey", "defense",
    "watch & learn", "schedule a consultation", "download the content",
    "data privacy notice", "sort by", "featured", "overview",
    "portfolio", "view all", "partners", "vendors", "brands",
    "innovation realm", "public key infrastructure",
    "logo footer", "logo header", "site logo", "company logo",
    "reseller", "distributor", "technology partner", "strategic partner",
    "authorised", "authorized", "certified", "accreditated",
    "drone safe store progressive", "open 9.00 17.30 mon sat",
    "14 day easy returns", "price match promise", "super speedy delivery",
    "click & collect", "forgot your password", "paypal credit available",
    "clearpay finance available", "dragons den winners",
    "highest rated", "largest uk indoor", "ship 7 days a week",
    "free next day delivery", "including weekends",
    "trade", "finance", "leasing", "asset leasing", "solar leasing",
    "contact us", "about us", "our services", "home",
    "navigation", "buying from us", "your cloud",
    "gdp policy", "gdpr policy", "modern slavery statement",
    "carbon reduction plan", "strategic business relationships",
    "olark live chat software",
}

NOISE_SUFFIXES = [
    "logo", "image", "icon", "graphic", "marble", "abstract",
    "software solutions", "admin console", "value incentive plan",
    "cloud solutions", "enterprise", "partner", "vendor",
    "featured", "badge", "button", "swag",
    "-mobile", "-desktop", "-tablet", "-hero", "-footer", "-header",
    "ink and toner cartridges", "printers & cartridges", "printers and cartridges",
    "ink and toner", "toner cartridges", "ink cartridges",
    "ecotank printers", "laser printers", "inkjet printers",
    "multfunction printers", "a3 printers", "printers",
    "ribbons", "scanners", "consumables",
    "ink tank printers",
    "gold partner", "silver partner", "bronze partner",
    "advanced partner", "certified partner", "authorized partner",
    "registered partner", "select partner", "premier partner",
    "enterprise partner", "global partner",
    "gold", "silver", "bronze", "advanced",
    "solutions", "systems", "equipment", "services",
]

PARKED_INDICATORS = [
    "domain is for sale", "this domain is for sale", "buy this domain",
    "make an offer", "domain for sale", "hugedomains", "sedo",
    "dan.com", "afternic", "escrow", "domain parking",
]

RELATIONSHIP_PAGE_PATHS = {
    "/brands": "brands",
    "/our-brands": "brands",
    "/brands-we-carry": "brands",
    "/distributed-brands": "brands",
    "/brands-we-distribute": "brands",
    "/partners": "partners",
    "/our-partners": "partners",
    "/technology-partners": "partners",
    "/strategic-partners": "partners",
    "/vendor": "vendors",
    "/vendors": "vendors",
    "/our-vendors": "vendors",
    "/suppliers": "vendors",
    "/our-suppliers": "vendors",
    "/distributors": "distributors",
    "/our-distributors": "distributors",
    "/distribution-partners": "distributors",
}

ALL_PATHS = list(RELATIONSHIP_PAGE_PATHS.keys()) + [
    "/products", "/solutions", "/brands-we-work-with", "/who-we-work-with",
    "/our-network", "/brands/we/distribute", "/our-brands-we-distribute",
]


def _fetch_page_urllib(url: str, timeout: int = FAST_TIMEOUT) -> Optional[str]:
    """Fallback fetcher using urllib with multiple TLS configs."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    ssl_configs = []
    ctx1 = ssl.create_default_context()
    ctx1.check_hostname = False
    ctx1.verify_mode = ssl.CERT_NONE
    ssl_configs.append(ctx1)

    try:
        ctx2 = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        ssl_configs.append(ctx2)
    except Exception:
        pass

    ssl_configs.append(ssl.create_default_context())

    for ctx in ssl_configs:
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            continue

    if url.startswith('https://'):
        http_url = url.replace('https://', 'http://', 1)
        try:
            req = urllib.request.Request(http_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            pass
    return None


def fetch_page(url: str, timeout: int = FAST_TIMEOUT) -> Optional[str]:
    """Fetch a page's HTML content."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    try:
        import requests
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        if resp.status_code in (202, 403, 429, 503):
            html = _fetch_page_urllib(url, timeout)
            if html:
                return html
            # Try cloudscraper for Cloudflare
            try:
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, timeout=timeout)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                pass
            return None
    except Exception:
        html = _fetch_page_urllib(url, timeout)
        if html:
            return html
        # Try cloudscraper
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass

    html = _fetch_page_urllib(url, timeout)
    if html:
        return html

    # Try cloudscraper as final fallback
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


async def _fetch_with_playwright_impl(url: str, timeout: int = 15000) -> Optional[str]:
    """Internal Playwright fetcher."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            content = await page.content()
            await browser.close()
            return content
    except Exception:
        return None


def fetch_with_playwright(url: str, timeout: int = 15000) -> Optional[str]:
    """Fetch a page with JavaScript rendering using Playwright."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_fetch_with_playwright_impl(url, timeout))


def is_parked_domain(html: str, url: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    visible_text = soup.get_text(separator=" ", strip=True).lower()
    hits = sum(1 for indicator in PARKED_INDICATORS if indicator in visible_text)
    return hits >= 1


def clean_brand_name(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[\"'\(\)\[\]]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" -:,.;|")

    if not re.search(r"[A-Za-z]", text):
        return ""
    if len(text) < 2 or len(text) > 80:
        return ""

    text_lower = text.lower()

    # FIRST: Strip suffixes before noise pattern check
    for suffix in NOISE_SUFFIXES:
        if text_lower.endswith(suffix):
            new_text = text[:-(len(suffix))].strip(" -:,.;|").strip()
            if new_text and len(new_text) >= 2:
                text = new_text
                text_lower = text.lower()
            else:
                return ""

    # NOW: Check noise patterns on the cleaned text
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text_lower):
            return ""
    if text_lower in NOISE_EXACT:
        return ""

    # Check if text contains any noise word as substring
    for noise_word in NOISE_EXACT:
        if len(noise_word) <= 4:
            continue
        if noise_word in text_lower:
            return ""

    if text_lower in NOISE_EXACT:
        return ""
    if re.search(r'\s\d+$', text):
        return ""
    if '%' in text or '=' in text or '&' in text:
        return ""

    if re.fullmatch(r"[a-z0-9 ]+", text_lower) and len(text.split()) > 4:
        return ""

    if re.search(r'\.(com|co\.uk|org|net|edu|gov|io|ai|ly|co|info|biz|ru|cn)', text_lower):
        return ""

    return text


def dedupe_brands(brands: list[str]) -> list[str]:
    seen = set()
    result = []
    for brand in brands:
        cleaned = clean_brand_name(brand)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def find_relationship_page_urls(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    base = base_url.rstrip("/")
    candidates = []

    priority_paths = ["/partners", "/our-partners", "/technology-partners", "/brands",
                     "/our-brands", "/vendors", "/our-vendors", "/distributors"]

    for path in priority_paths:
        candidates.append(base + path)

    for path in ALL_PATHS:
        full_url = base + path
        if full_url not in candidates:
            candidates.append(full_url)

    keywords = ["brand", "partner", "vendor", "distributor", "supplier"]
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text().lower()
        if href.startswith("http") and not href.startswith(base):
            continue
        if any(kw in text or kw in href.lower() for kw in keywords):
            from urllib.parse import urljoin
            full_url = urljoin(base_url, href)
            if full_url not in candidates:
                candidates.append(full_url)

    return candidates[:10]


def extract_relationships_from_page(soup: BeautifulSoup, url: str, category: str) -> list[str]:
    names = []

    # Method 1: Logo images - MOST RELIABLE
    logo_names = []
    for img in soup.find_all("img"):
        alt = img.get("alt", "").strip()

        if not alt or len(alt) < 2:
            continue
        alt_lower = alt.lower()
        if alt_lower in ["logo", "image", "icon", "button", "banner"]:
            continue
        if alt_lower.startswith("http"):
            continue

        if "partner" in alt_lower:
            brand = alt_lower.replace("partner", "").strip()
            brand = re.sub(r'[^a-zA-Z0-9\s\-]', '', brand).strip()
            if brand and len(brand) > 1:
                logo_names.append(brand.title())
            continue

        skip_words = ["menu", "home", "contact", "about", "search", "login", "footer", "header", "nav"]
        alt_words = set(re.findall(r'\b\w+\b', alt_lower))
        if any(word in alt_words for word in skip_words):
            continue

        if len(alt.split()) > 5:
            continue

        cleaned = clean_brand_name(alt)
        if cleaned and len(cleaned) >= 2:
            logo_names.append(cleaned)

    names.extend(logo_names)

    # Only use text-based methods if logos found fewer than 3
    if len(logo_names) < 3:
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = heading.get_text(" ", strip=True).strip()
            if not text or len(text) < 3 or len(text) > 50:
                continue
            text_lower = text.lower()
            if any(word in text_lower for word in ["menu", "contact", "about", "home", "login", "search", "footer", "header", "nav", "copyright"]):
                continue
            if re.search(r'\d+.*(road|street|ave|avenue|house|building|floor|suite|unit)', text_lower):
                continue
            if any(phrase in text_lower for phrase in ["had a call", "call from", "contact us", "get in touch", "send us", "key benefits", "insightful", "marketing programs", "life at", "corporate social", "partner with us", "get started", "making a decision", "need help"]):
                continue
            if '@' in text or '.co.uk' in text_lower or '.com' in text_lower:
                continue
            cleaned = clean_brand_name(text)
            if cleaned and len(cleaned) >= 3:
                names.append(cleaned)

        for bold in soup.find_all(["b", "strong", "span"]):
            text = bold.get_text(" ", strip=True).strip()
            if not text or len(text) < 3 or len(text) > 60:
                continue
            text_lower = text.lower()
            skip_words = ["menu", "contact", "about", "home", "login", "search", "footer", "header", "nav", "www", ".co.uk", ".com", "@", "road", "street", "avenue", "house", "copyright", "key benefits", "insightful", "marketing", "get my", "built for", "today's", "for ", "environment", "help ag"]
            if any(word in text_lower for word in skip_words):
                continue
            cleaned = clean_brand_name(text)
            if cleaned and len(cleaned) >= 3:
                names.append(cleaned)

    return dedupe_brands(names)


def get_generic_email(url: str) -> tuple[str, str]:
    """Get generic email for a domain."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain_clean = parsed.netloc.replace('www.', '')
    domain_base = domain_clean.split('.')[0]
    generic_prefixes = ["info", "sales", "contact", "hello", "general", "support", "admin", "office"]

    # Try homepage first
    homepage_url = f'https://www.{domain_clean}'
    html = fetch_page(homepage_url, timeout=FAST_TIMEOUT)
    if html:
        emails = extract_emails_from_html(html)
        if emails:
            business_emails = set()
            for email in emails:
                email_domain = email.split('@')[1]
                if domain_clean in email_domain or email_domain.split('.')[0] == domain_base:
                    business_emails.add(email)
            final_emails = business_emails if business_emails else emails
            for prefix in generic_prefixes:
                for email in sorted(final_emails):
                    if email.lower().startswith(prefix + "@"):
                        return email, homepage_url
            return sorted(final_emails)[0] if final_emails else "", ""

    # Try /contact
    contact_url = f'https://www.{domain_clean}/contact'
    html = fetch_page(contact_url, timeout=FAST_TIMEOUT)
    if html:
        emails = extract_emails_from_html(html)
        if emails:
            business_emails = set()
            for email in emails:
                email_domain = email.split('@')[1]
                if domain_clean in email_domain or email_domain.split('.')[0] == domain_base:
                    business_emails.add(email)
            final_emails = business_emails if business_emails else emails
            for prefix in generic_prefixes:
                for email in sorted(final_emails):
                    if email.lower().startswith(prefix + "@"):
                        return email, contact_url
            return sorted(final_emails)[0] if final_emails else "", ""

    return "", ""


EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
MAILTO_PATTERN = re.compile(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})')
CF_EMAIL_PATTERN = re.compile(r'data-cfemail="([a-f0-9]+)"')
CF_HREF_PATTERN = re.compile(r'/cdn-cgi/l/email-protection#([a-f0-9]+)')

SKIP_EMAIL_WORDS = [
    'sentry.io', 'wixpress', 'example.com', '.png', '.jpg', '.svg', '.gif',
    '.webp', 'webpack', 'sentry', '@2x', '@media', '@import', '@font',
    '@keyframe', 'user@domain', 'email@email', '@screen', '@charset',
    '@tailwind', '@Apply', '@layer', 'noreply', '@click', '@submit',
]


def decode_cf_email(encoded: str) -> Optional[str]:
    """Decode Cloudflare email protection."""
    try:
        r = int(encoded[:2], 16)
        email = ''
        for i in range(2, len(encoded), 2):
            email += chr(int(encoded[i:i+2], 16) ^ r)
        return email if '@' in email else None
    except Exception:
        return None


def is_valid_email(email: str) -> bool:
    e = email.lower()
    if any(skip in e for skip in SKIP_EMAIL_WORDS):
        return False
    if e.endswith('.wixsite.com') or e.endswith('.squarespace.com'):
        return False
    parts = e.split('@')
    if len(parts) != 2:
        return False
    domain_part = parts[1]
    if '.' not in domain_part:
        return False
    return True


def extract_emails_from_html(html: str) -> set:
    """Extract all email addresses from HTML content."""
    emails = set()
    for match in EMAIL_PATTERN.findall(html):
        if is_valid_email(match):
            emails.add(match.lower())
    for match in MAILTO_PATTERN.findall(html):
        if is_valid_email(match):
            emails.add(match.lower())
    for encoded in CF_EMAIL_PATTERN.findall(html):
        decoded = decode_cf_email(encoded)
        if decoded and is_valid_email(decoded):
            emails.add(decoded.lower())
    for encoded in CF_HREF_PATTERN.findall(html):
        decoded = decode_cf_email(encoded)
        if decoded and is_valid_email(decoded):
            emails.add(decoded.lower())
    return emails


def scrape_company(url: str, company_name: str = "") -> dict:
    """
    Scrape a company website for brands and email.
    Returns dict with:
        - success: bool
        - company_name: str
        - generic_email: str
        - email_source_url: str
        - brands: str (pipe-separated)
        - brands_source_url: str
        - brand_categories: str
        - error: str
        - needs_manual: bool (True if blocked/failed and needs manual entry)
    """
    from urllib.parse import urlparse

    result = {
        "success": False,
        "company_name": company_name,
        "generic_email": "",
        "email_source_url": "",
        "brands": "",
        "brands_source_url": "",
        "brand_categories": "",
        "error": "",
        "needs_manual": False,
    }

    # Normalize URL
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.path == "/" or parsed.path == "":
        if not parsed.netloc.startswith("www."):
            url = url.replace("://" + parsed.netloc, "://www." + parsed.netloc, 1)
    url = url.rstrip("/")
    company_domain = parsed.netloc.lower().replace("www.", "")

    try:
        # Get homepage
        html = fetch_page(url, timeout=15)
        if not html:
            result["error"] = "Failed to fetch homepage (blocked or unreachable)"
            result["needs_manual"] = True
            return result

        if is_parked_domain(html, url):
            result["error"] = "Domain appears to be parked or for sale"
            result["needs_manual"] = True
            return result

        # Extract email
        email, email_url = get_generic_email(url)
        result["generic_email"] = email
        result["email_source_url"] = email_url

        # Find relationship pages
        page_urls = find_relationship_page_urls(url, html)
        all_names = []

        for page_url in page_urls[:MAX_BRAND_PAGES]:
            page_html = fetch_page(page_url, timeout=8)
            if not page_html:
                continue
            soup = BeautifulSoup(page_html, "html.parser")
            names = extract_relationships_from_page(soup, page_url, "partners")
            if len(names) >= 3:
                all_names.extend(names)
                result["brands_source_url"] = page_url
                break

        # Also try homepage if no results
        if not all_names:
            soup = BeautifulSoup(html, "html.parser")
            names = extract_relationships_from_page(soup, url, "partners")
            if names:
                all_names = names

        # Fallback to Playwright if fewer than 3 results
        if len(all_names) < 3:
            for page_url in page_urls[:MAX_BRAND_PAGES]:
                js_html = fetch_with_playwright(page_url, timeout=20000)
                if js_html:
                    soup = BeautifulSoup(js_html, "html.parser")
                    names = extract_relationships_from_page(soup, page_url, "partners")
                    if len(names) >= 3:
                        all_names = names
                        result["brands_source_url"] = page_url
                        break

            if not all_names:
                js_html = fetch_with_playwright(url, timeout=20000)
                if js_html:
                    soup = BeautifulSoup(js_html, "html.parser")
                    names = extract_relationships_from_page(soup, url, "partners")
                    if names:
                        all_names = names

        # Filter self-references
        company_name_lower = company_name.lower() if company_name else ""
        unique_names = []
        seen = set()
        for name in all_names:
            key = name.lower()
            if key in seen:
                continue
            if company_name_lower and (company_name_lower in key or key in company_name_lower):
                continue
            skip = False
            for existing in seen:
                if key in existing or existing in key:
                    skip = True
                    break
            if skip:
                continue
            seen.add(key)
            unique_names.append(name)

        result["brands"] = " | ".join(unique_names[:50])
        result["success"] = True

        # If we got no data, mark for manual review
        if not result["brands"] and not result["generic_email"]:
            result["error"] = "No data found automatically"
            result["needs_manual"] = True

    except Exception as e:
        result["error"] = str(e)
        result["needs_manual"] = True

    return result


# Category keywords for auto-categorization
CATEGORY_KEYWORDS = {
    "10 Servers": ["server", "blade server", "rack server", "tower server", "data center", "dell", "dell technologies", "dell poweredge", "hp server", "hpe server", "lenovo server", "supermicro", "ibm server", "oracle server", "cisco server"],
    "11 Server Options": ["server ram", "server cpu", "raid controller", "server part", "server accessory", "server component", "server hardware", "dell raid", "hp raid", "server memory", "processor", "kingston", "kingston technology", "ram", "ssd", "solid state drive"],
    "12 Storage": ["storage", "nas", "san", "hard drive", "ssd", "solid state", "disk array", "tape library", "storage array", "network storage", "san storage", "das", "storage system", "qnap", "synology", "netapp", "dell emc", "hp storage", "hpe storage", "wd", "western digital", "seagate", "seagate technology", "toshiba", "wdc"],
    "13 Networking": ["router", "switch", "firewall", "access point", "network", "ethernet", "cable", "modem", "wan", "lan", "cisco", "juniper", "netgear", "tp-link", "ubiquiti", "aruba", "hpe networking", "dell networking", "fortinet", "palo alto", "meraki", "wireless", "wlan", "poe", "network switch", "firewall appliance", "network router"],
    "14 Desktop": ["desktop", "pc", "workstation", "all-in-one", "mini pc", "dell optiplex", "hp desktop", "hp inc", "lenovo desktop", "acer desktop", "asus desktop", "office pc", "business pc", "computer", "商用电脑", "商务机"],
    "15 Notebook": ["laptop", "notebook", "chromebook", "ultrabook", "macbook", "dell latitude", "hp elitebook", "hp probook", "lenovo thinkpad", "lenovo yoga", "asus laptop", "acer laptop", "microsoft surface", "gaming laptop", "mobile workstation", "lenovo", "笔记本"],
    "16 Printers and Photocopier": ["printer", "photocopier", "copier", "mfp", "multifunction printer", "laser printer", "inkjet printer", "office printer", "printers", "kyocera", "xerox", "canon", "canon printer", "epson printer", "brother printer", "hp printer", "samsung printer", "ricoh", "sharp", "toshiba", "konica minolta", "zebra printer", "label printer", "printers and photocopier", "佳能"],
    "17 Supplies": ["toner", "ink", "cartridge", "label", "ribbon", "consumable", "printer cartridge", "ink cartridge", "toner cartridge", "label maker", "printer paper", "office supplies", "printer supplies", "imaging supplies", "filing supplies", "hp supplies", "canon supplies", "epson supplies"],
    "18 Scanners": ["scanner", "barcode scanner", "document scanner", "3d scanner", "barcode reader", "qr scanner", "scanners", "fujitsu scanner", "epson scanner", "canon scanner", "brother scanner", "honeywell scanner", "zebra scanner", "datalogic", "cognex", "epson"],
    "19 Surveillance": ["camera", "cctv", "surveillance", "security camera", "nvr", "dvr", "monitoring", "ip camera", "security system", "cctv camera", "dahua", "hikvision", "axis camera", "bosch camera", "swann", "lorex", "ring", "nest", "arlo", "video surveillance", "access control", "安防", "监控"],
    "20 UPS and Power Systems": ["ups", "power supply", "inverter", "battery backup", "generator", "pdu", "power protection", "apc", "apc by schneider electric", "eaton ups", "tripp lite", "cyberpower", "ups battery", "power conditioner", "surge protector", "rack pdu", "power distribution", "uninterruptible power supply"],
    "21 Cables": ["cable", "connector", "adapter", "usb cable", "ethernet cable", "fiber optic", "hdmi cable", "vga cable", "displayport", "dvi cable", "serial cable", "power cable", "network cable", "fiber cable", "copper cable", "cabling", "cable management", "patch cable", "cat6", "cat5e", "cat7", "belkin", "cable matters", "startech"],
    "22 Mobiles and Tablets": ["mobile", "phone", "smartphone", "tablet", "iphone", "android", "ipad", "samsung", "samsung galaxy", "apple iphone", "google pixel", "oneplus", "xiaomi", "huawei phone", "sony xperia", "lg phone", "nokia", "motorola", "rugged phone", "rugged tablet", "mobile device", "智能手机"],
    "23 Software": ["software", "license", "subscription", "saas", "cloud service", "microsoft", "microsoft 365", "office 365", "adobe", "autocad", "vmware", "oracle", "sap", "salesforce", "slack", "zoom", "antivirus", "security software", "accounting software", "erp", "crm", "backup software", "software solution", "software provider"],
    "24 Gaming Products": ["gaming", "game console", "playstation", "xbox", "nintendo", "sony", "gaming chair", "gaming mouse", "gaming keyboard", "gaming headset", "gaming monitor", "gaming laptop", "gaming pc", "steam", "gaming controller", "razer", "logitech g", "corsair gaming", "asus rog", "alienware", "gaming accessories", "gamer"],
    "25 Tech Furniture": ["desk", "workstation desk", "cabinet", "mount", "stand", "rack mount", "monitor arm", "monitor stand", "laptop stand", "tablet stand", "phone stand", "keyboard tray", "desk mount", "wall mount", "cabinet", "storage cabinet", "filing cabinet", "tech furniture", "sit stand desk", "adjustable desk", "apc furniture", "server rack"],
    "26 Synergy": [],
    "32 Services and Support": ["support", "maintenance", "managed service", "it service", "consulting", "installation", "it support", "technical support", "helpdesk", "service contract", "maintenance contract", "it maintenance", "computer repair", "laptop repair", "printer repair", "network support", "cloud services", "managed it", "it outsourcing", "it consultancy", "infosys", "tech support", "repair", "installation services"],
}


def auto_assign_categories(brands_text: str) -> str:
    """Auto-assign categories based on brands text."""
    if not brands_text:
        return ""

    brands_lower = brands_text.lower()
    assigned = set()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "26 Synergy":
            continue  # Only assign if nothing else fits
        for keyword in keywords:
            if keyword in brands_lower:
                assigned.add(category.split(" ")[0])  # Get just the number
                break

    # If nothing assigned, mark as Synergy
    if not assigned:
        assigned.add("26")

    return ", ".join(sorted(assigned))
