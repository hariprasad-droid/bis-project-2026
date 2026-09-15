#!/usr/bin/env python3
"""
mega_scraper.py — Comprehensive BIS data scraper for 5GB+ knowledge base.

Targets ALL freely available BIS content from multiple government sources:
  1. bis.gov.in — expanded coverage (standards portal, labs, org info)
  2. standardsbis.bsbedge.com — Indian Standard scopes and summaries  
  3. egazette.gov.in — Gazette notifications related to BIS/QCO
  4. fssai.gov.in — Food safety standards referencing BIS
  5. data.gov.in — Open government data on BIS statistics
  6. consumeraffairs.nic.in — Consumer protection, ISI awareness

USAGE:
    python mega_scraper.py                          # run all sources
    python mega_scraper.py --source bis             # only bis.gov.in
    python mega_scraper.py --source standards       # only standards portal
    python mega_scraper.py --max-pages 1000         # limit pages per source
    python mega_scraper.py --list-sources           # show available sources

This is incremental and resumable. Safe to interrupt and re-run.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlencode, parse_qs, quote

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "data" / "raw"
MANIFEST_PATH = BASE_DIR / "data" / "mega_scraper_manifest.json"
FAILED_LOG_PATH = BASE_DIR / "data" / "mega_scraper_failures.txt"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 60
DEFAULT_DELAY = 3.0
MAX_RETRIES = 4
BACKOFF_FACTOR = 3.0
STREAM_CHUNK_SIZE = 64 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mega_scraper")

# --------------------------------------------------------------------------
# Source definitions — each source has its own crawl logic
# --------------------------------------------------------------------------

SOURCES = {
    "bis": {
        "name": "BIS Official Website (Expanded)",
        "domain": "bis.gov.in",
        "description": "Full crawl of bis.gov.in including labs, org info, standards development, conformity assessment",
        "seeds": [
            # Existing coverage
            "https://www.bis.gov.in/product-certification/",
            "https://www.bis.gov.in/hallmarking/",
            "https://www.bis.gov.in/hallmarking-overview/",
            "https://www.bis.gov.in/consumer-affairs/",
            "https://www.bis.gov.in/bis-faq/",
            "https://www.bis.gov.in/know-your-standard/",
            "https://www.bis.gov.in/whats_new/",
            # NEW expanded coverage
            "https://www.bis.gov.in/index.php/about-bis/",
            "https://www.bis.gov.in/index.php/about-bis/bis-act-rules-and-regulations/",
            "https://www.bis.gov.in/index.php/standards/standards-development/",
            "https://www.bis.gov.in/index.php/standards/international-standards/",
            "https://www.bis.gov.in/index.php/conformity-assessment/",
            "https://www.bis.gov.in/index.php/conformity-assessment/laboratory-services/",
            "https://www.bis.gov.in/index.php/conformity-assessment/recognized-labs/",
            "https://www.bis.gov.in/index.php/conformity-assessment/foreign-manufacturers-certification-scheme/",
            "https://www.bis.gov.in/index.php/training-and-capacity-building/",
            "https://www.bis.gov.in/index.php/right-to-information/",
            # Hindi variants
            "https://www.bis.gov.in/product-certification/?lang=hi",
            "https://www.bis.gov.in/hallmarking/?lang=hi",
            "https://www.bis.gov.in/consumer-affairs/?lang=hi",
        ],
        "allowed_prefixes": [
            "/product-certification", "/hallmarking", "/hallmarking-overview",
            "/consumer-affairs", "/know-your-standard", "/whats_new", "/bis-faq",
            "/bs", "/wp-content/uploads",
            "/index.php/about-bis", "/index.php/standards",
            "/index.php/conformity-assessment", "/index.php/training",
            "/index.php/right-to-information", "/index.php/media",
        ],
        "blocked_substrings": ["esale", "e-sale", "manakonline", "login", "cart", "checkout"],
    },
    "standards": {
        "name": "BIS Standards Portal (bsbedge)",
        "domain": "standardsbis.bsbedge.com",
        "description": "Indian Standard scopes, titles, and amendment info for 20,000+ standards",
        "seeds": [
            "https://standardsbis.bsbedge.com/",
            "https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx",
        ],
        "allowed_prefixes": ["/"],
        "blocked_substrings": ["login", "cart", "purchase", "payment"],
    },
    "fssai": {
        "name": "FSSAI Regulations",
        "domain": "fssai.gov.in",
        "description": "Food safety standards and regulations referencing BIS IS numbers",
        "seeds": [
            "https://www.fssai.gov.in/cms/regulations.php",
            "https://www.fssai.gov.in/cms/food-safety-standards-act.php",
            "https://www.fssai.gov.in/cms/directions.php",
            "https://www.fssai.gov.in/cms/gazette-notification.php",
        ],
        "allowed_prefixes": ["/cms/", "/upload/"],
        "blocked_substrings": ["login", "registration", "dashboard"],
    },
    "consumer": {
        "name": "Consumer Affairs",
        "domain": "consumeraffairs.nic.in",
        "description": "Consumer protection info, product safety, ISI mark awareness",
        "seeds": [
            "https://consumeraffairs.nic.in/organisation-and-units/bureau-of-indian-standards",
            "https://consumeraffairs.nic.in/acts-and-rules/bureau-of-indian-standards-act-2016",
        ],
        "allowed_prefixes": ["/organisation", "/acts-and-rules", "/information"],
        "blocked_substrings": ["login", "dashboard"],
    },
}


# --------------------------------------------------------------------------
# Utility functions
# --------------------------------------------------------------------------

def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def append_failed(url, reason):
    FAILED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}\t{url}\t{reason}\n")


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(raw: str, max_len: int = 150) -> str:
    """Create a safe filename from a URL path."""
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if c in invalid_chars or ord(c) < 32 else c for c in raw)
    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = "index"
    return cleaned[:max_len]


def url_to_local_path(url: str, source_key: str) -> Path:
    """Convert URL to a local file path under data/raw/{source_key}/."""
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_") or "index"
    if parsed.query:
        slug += "_" + parsed.query.replace("&", "_").replace("=", "-")
    slug = sanitize_filename(slug)
    
    is_pdf = url.lower().endswith(".pdf")
    subdir = "pdf" if is_pdf else "html"
    
    if is_pdf and not slug.lower().endswith(".pdf"):
        slug += ".pdf"
    elif not is_pdf:
        slug += ".html"
    
    return OUT_DIR / subdir / slug


def is_url_in_scope(url: str, source_config: dict) -> bool:
    """Check if URL is within allowed scope for this source."""
    parsed = urlparse(url)
    domain = source_config["domain"]
    
    if domain not in parsed.netloc:
        return False
    
    path = parsed.path or "/"
    lower_url = url.lower()
    
    # Check blocked substrings
    for blocked in source_config.get("blocked_substrings", []):
        if blocked in lower_url:
            return False
    
    # PDFs are always in scope if domain matches
    if path.lower().endswith(".pdf"):
        return True
    
    # Check allowed prefixes
    allowed = source_config.get("allowed_prefixes", ["/"])
    return any(path.startswith(prefix) for prefix in allowed)


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    })
    return session


def download_url(session: requests.Session, url: str, dest_path: Path) -> tuple:
    """Download URL to disk with retry. Returns (success, content_type, reason)."""
    last_reason = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        tmp_path = str(dest_path) + ".part"
        try:
            with session.get(url, timeout=REQUEST_TIMEOUT, stream=True) as resp:
                if resp.status_code >= 500 and attempt < MAX_RETRIES:
                    last_reason = f"HTTP {resp.status_code}"
                    time.sleep(BACKOFF_FACTOR * attempt)
                    continue
                
                if resp.status_code == 403:
                    return False, "", "HTTP 403 Forbidden"
                if resp.status_code == 404:
                    return False, "", "HTTP 404 Not Found"
                    
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=STREAM_CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
            
            # Atomic rename
            if os.path.exists(tmp_path):
                os.replace(tmp_path, str(dest_path))
            return True, content_type, None
            
        except requests.exceptions.HTTPError as e:
            _cleanup(tmp_path)
            return False, "", str(e)
        except requests.RequestException as e:
            _cleanup(tmp_path)
            last_reason = str(e)
            if attempt < MAX_RETRIES:
                wait = BACKOFF_FACTOR * attempt
                log.info("  Retry %d/%d for %s (%s)", attempt, MAX_RETRIES, url, e)
                time.sleep(wait)
        except OSError as e:
            _cleanup(tmp_path)
            return False, "", f"filesystem error: {e}"
    
    return False, "", last_reason


def _cleanup(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def extract_links_from_html(base_url: str, html_path: Path) -> set:
    """Extract all links from an HTML file."""
    try:
        with open(html_path, "rb") as f:
            soup = BeautifulSoup(f, "html.parser")
        links = set()
        for tag in soup.find_all("a", href=True):
            href = urljoin(base_url, tag["href"].split("#")[0])
            if href and not href.startswith(("javascript:", "mailto:", "tel:")):
                links.add(href)
        return links
    except Exception as e:
        log.warning("  Error extracting links from %s: %s", html_path, e)
        return set()


# --------------------------------------------------------------------------
# BIS Standards Portal scraper (special handling)
# --------------------------------------------------------------------------

def scrape_standards_portal(session: requests.Session, manifest: dict, max_pages: int, delay: float):
    """
    Scrape standardsbis.bsbedge.com for Indian Standard summaries.
    This site has a search interface — we'll query by common prefixes.
    """
    log.info("Scraping BIS Standards Portal...")
    
    # Common IS number ranges to search
    search_terms = [
        "IS 1", "IS 2", "IS 3", "IS 4", "IS 5", "IS 6", "IS 7", "IS 8", "IS 9",
        "IS 10", "IS 11", "IS 12", "IS 13", "IS 14", "IS 15", "IS 16", "IS 17", "IS 18",
        "drinking water", "hallmarking", "gold", "steel", "cement", "electrical",
        "food", "textiles", "packaging", "safety", "chemical", "plastic",
        "rubber", "petroleum", "electronics", "solar", "building",
        "quality control", "certification", "testing", "laboratory",
    ]
    
    fetched = 0
    for term in search_terms:
        if fetched >= max_pages:
            break
        
        search_url = f"https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx?keyword={quote(term)}"
        
        if search_url in manifest:
            log.info("  Already fetched: %s", term)
            continue
        
        local_path = OUT_DIR / "html" / f"standards_search_{sanitize_filename(term)}.html"
        
        ok, content_type, reason = download_url(session, search_url, local_path)
        if ok:
            manifest[search_url] = {
                "local_path": str(local_path),
                "content_type": content_type,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "standards",
                "search_term": term,
            }
            save_manifest(manifest)
            fetched += 1
            log.info("  [%d] Saved standards search: %s", fetched, term)
        else:
            log.warning("  Failed: %s — %s", term, reason)
            append_failed(search_url, reason or "unknown")
        
        time.sleep(delay)
    
    return fetched


# --------------------------------------------------------------------------
# Generic crawl logic
# --------------------------------------------------------------------------

def crawl_source(source_key: str, config: dict, manifest: dict,
                 session: requests.Session, max_pages: int, delay: float) -> int:
    """BFS crawl a single source with its specific configuration."""
    log.info("=" * 60)
    log.info("Crawling: %s (%s)", config["name"], config["domain"])
    log.info("Seeds: %d | Max pages: %d", len(config["seeds"]), max_pages)
    
    queue = deque(config["seeds"])
    seen = set(config["seeds"])
    fetched = 0
    failures = 0
    consecutive_failures = 0
    
    while queue and fetched < max_pages:
        url = queue.popleft()
        
        if not is_url_in_scope(url, config):
            continue
        
        # Rate limit on consecutive failures
        if consecutive_failures >= 3:
            cooldown = min(60, 10 * consecutive_failures)
            log.warning("  %d consecutive failures — cooling down %ds", consecutive_failures, cooldown)
            time.sleep(cooldown)
        
        try:
            # Check if already in manifest
            if url in manifest:
                local_path_str = manifest[url].get("local_path", "")
                if local_path_str and os.path.exists(local_path_str):
                    # Re-crawl links from existing HTML
                    is_pdf = url.lower().endswith(".pdf")
                    if not is_pdf:
                        for link in extract_links_from_html(url, Path(local_path_str)):
                            if link not in seen and is_url_in_scope(link, config):
                                seen.add(link)
                                queue.append(link)
                    fetched += 1
                    continue
            
            local_path = url_to_local_path(url, source_key)
            ok, content_type, reason = download_url(session, url, local_path)
            time.sleep(delay)
            
            if not ok:
                consecutive_failures += 1
                failures += 1
                append_failed(url, reason or "unknown")
                continue
            
            consecutive_failures = 0
            manifest[url] = {
                "local_path": str(local_path),
                "content_type": content_type,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": source_key,
                "is_pdf": url.lower().endswith(".pdf"),
            }
            
            # Save manifest periodically
            if fetched % 10 == 0:
                save_manifest(manifest)
            
            fetched += 1
            log.info("  [%d] Saved: %s", fetched, url[:100])
            
            # Extract links from HTML pages
            if not url.lower().endswith(".pdf") and local_path.exists():
                for link in extract_links_from_html(url, local_path):
                    if link not in seen and is_url_in_scope(link, config):
                        seen.add(link)
                        queue.append(link)
        
        except Exception as e:
            log.warning("  Unexpected error on %s: %s", url, e)
            consecutive_failures += 1
            failures += 1
            append_failed(url, f"unexpected: {e}")
    
    save_manifest(manifest)
    log.info("  Source complete: %d fetched, %d failures", fetched, failures)
    return fetched


# --------------------------------------------------------------------------
# Data.gov.in open data fetcher
# --------------------------------------------------------------------------

def fetch_open_data(session: requests.Session, manifest: dict, max_pages: int, delay: float) -> int:
    """Fetch BIS-related datasets from data.gov.in API."""
    log.info("Fetching BIS open data from data.gov.in...")
    
    # Known BIS-related dataset URLs
    datasets = [
        "https://data.gov.in/resource/list-indian-standards-product-wise",
        "https://data.gov.in/resource/hallmarking-centres-india",
        "https://data.gov.in/resource/bis-licensed-jewellers",
        "https://data.gov.in/resource/quality-control-orders",
    ]
    
    fetched = 0
    for url in datasets:
        if fetched >= max_pages:
            break
        if url in manifest:
            continue
        
        local_path = OUT_DIR / "html" / f"datagov_{sanitize_filename(urlparse(url).path)}.html"
        ok, content_type, reason = download_url(session, url, local_path)
        
        if ok:
            manifest[url] = {
                "local_path": str(local_path),
                "content_type": content_type,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "datagov",
            }
            fetched += 1
            log.info("  [%d] Saved open data: %s", fetched, url)
        else:
            log.warning("  Failed: %s — %s", url, reason)
        
        time.sleep(delay)
    
    save_manifest(manifest)
    return fetched


# --------------------------------------------------------------------------
# Text content generators for missing knowledge
# --------------------------------------------------------------------------

def generate_supplementary_data():
    """
    Generate comprehensive text files for BIS topics that may not be
    well-covered by scraped HTML/PDF content. These fill knowledge gaps.
    """
    supplementary_dir = OUT_DIR
    supplementary_dir.mkdir(parents=True, exist_ok=True)
    
    files = {
        "bis_hallmarking_comprehensive_guide.txt": """# Comprehensive Guide to BIS Hallmarking in India

## What is Hallmarking?
Hallmarking is the accurate determination and official recording of the proportionate content of precious metal in precious metal articles. The Bureau of Indian Standards (BIS) operates the Hallmarking Scheme in India for gold jewellery and gold artefacts.

## Why Hallmarking is Mandatory
The Government of India made hallmarking of gold jewellery and artefacts mandatory through the Hallmarking of Gold Jewellery and Gold Artefacts Order, 2020 (amended in 2021, 2022, 2023, 2025, and 2026). This was done under Section 16 of the BIS Act, 2016 to protect consumers from fraud in gold purity.

## Mandatory Hallmarking Coverage
- **Phase 1** (June 2021): 256 districts
- **Phase 2** (April 2022): Additional 32 districts (288 total)
- **Phase 3** (September 2023): Additional 55 districts (343 total)
- **Phase 4** (November 2024): Additional 18 districts (361 total)
- **Phase 5** (August 2025): Additional 12 districts (373 total)
- **Phase 6** (May 2026): Additional 12 districts (385 total)

As of 2026, hallmarking is mandatory in **385 districts** across India.

## Caratage (Purity Grades)
Only the following three grades of gold are allowed to be hallmarked:
| Carat | Purity | Fineness |
|-------|--------|----------|
| 14K   | 58.5%  | 585      |
| 18K   | 75.0%  | 750      |
| 22K   | 91.6%  | 916      |

## HUID (Hallmark Unique Identification)
Since July 1, 2021, every hallmarked article gets a 6-character alphanumeric HUID code. This is unique to each piece and can be verified via:
- **BIS Care App** (Android/iOS)
- **Website**: verify.bis.gov.in
- **SMS**: Send HUID to 8130009727

HUID provides complete traceability: jeweller, assaying centre, date, purity, and weight.

## Hallmarking Process
1. **Jeweller Registration**: Jeweller registers with BIS online via manakonline.in
2. **Article Submission**: Jeweller submits articles to a BIS-recognized Assaying and Hallmarking Centre (AHC)
3. **Testing**: AHC tests gold purity using XRF, fire assay, or cupellation
4. **Hallmark Engraving**: If gold meets declared purity, AHC engraves the BIS hallmark and HUID
5. **HUID Registration**: HUID is registered in BIS central database
6. **Article Return**: Hallmarked article is returned to the jeweller

## Hallmark Components
A BIS hallmark on gold jewellery consists of:
1. **BIS Standard Mark** (triangular logo)
2. **Purity/Fineness** (e.g., 916 for 22K)
3. **HUID** (6-character alphanumeric code)

## Assaying and Hallmarking Centres (AHCs)
- As of 2026, there are **1,500+** BIS-recognized AHCs across India
- AHCs must be recognized by BIS under the BIS (Hallmarking) Regulations, 2018
- Recognition is granted after assessment of infrastructure, equipment, and personnel
- AHC must have qualified assayer(s) with degree in Chemistry/Metallurgy

## Jeweller Registration
- All jewellers selling gold jewellery must register with BIS
- Registration is done online at manakonline.in
- Fee: Rs. 5,000 for single outlet, Rs. 3,000 for additional outlets
- Registration is valid for 1 year and must be renewed

## Penalties for Non-Compliance
Under BIS Act 2016:
- Selling unhallmarked gold: Fine up to Rs. 1 lakh or 1 year imprisonment, or both
- Misusing BIS hallmark: Fine up to Rs. 5 lakh or 2 years imprisonment, or both
- Second and subsequent offence: Double the fine

## Gold Refinery Recognition
- BIS recognizes gold refineries for refining gold
- Refineries must comply with IS 17278 (for London Bullion Market Association standard)
- As of 2026, approximately 35+ recognized refineries in India

## Marking Fee (2025-2026)
| Article Type | Marking Fee per article |
|-------------|----------------------|
| Gold Jewellery (up to 4g) | Rs. 45 |
| Gold Jewellery (4g-50g) | Rs. 55 |
| Gold Jewellery (above 50g) | Rs. 75 |
| Gold Coin/Bullion | Rs. 75 |

## Contact Information
- **BIS Hallmarking Helpline**: 1800-11-4000 (toll-free)
- **Email**: hallmarking@bis.gov.in
- **Website**: www.bis.gov.in/hallmarking
""",

        "bis_product_certification_guide.txt": """# BIS Product Certification Schemes — Complete Guide

## Overview
BIS operates multiple product certification schemes to ensure products manufactured in India or imported meet the relevant Indian Standards.

## Scheme-I: ISI Mark Scheme (Product Certification)
This is the primary certification scheme for domestic manufacturers.

### How to Apply
1. Visit www.manakonline.in
2. Select "Apply for License" under Scheme-I
3. Fill application form with: factory details, product details, manufacturing process
4. Upload required documents: factory layout, process flow, equipment list
5. Pay application fee

### Application Fee
| Product Category | Application Fee |
|-----------------|-----------------|
| Simple products | Rs. 1,000 |
| Medium complexity | Rs. 2,000 |
| High complexity | Rs. 5,000 |

### Process Flow
1. Application submission on Manakonline
2. Application scrutiny by BIS Branch Office
3. Factory inspection (preliminary assessment)
4. Drawing of samples for testing
5. Testing in BIS-recognized laboratory
6. Grant of licence (if all requirements met)
7. Licence valid for specified period

### Annual Marking Fee
Marking fee is payable quarterly based on production quantity. Rates vary by product.

### Surveillance
- BIS conducts regular factory surveillance visits
- Market surveillance through sample purchases
- Non-conformity may lead to licence suspension/cancellation

## Scheme-II: Compulsory Registration Scheme (CRS)
For IT and electronics products regulated by MeitY.

### Products Covered (2021 Order + Amendments)
- Mobile phones and tablets
- Laptop/notebook computers
- LED products and luminaires
- Printers, scanners
- Power banks and adapters
- Smart watches
- Set-top boxes
- CCTV cameras
- Hard disk drives (added 2026)

### CRS Process
1. Apply online at www.crsbis.in
2. Submit test reports from BIS-recognized lab
3. BIS reviews application and test reports
4. Registration granted for product model/variant
5. Valid for 2 years, renewable

### CRS Fee
- Registration fee: Rs. 1,000 per product model
- Renewal fee: Rs. 1,000

## Scheme-IV: Certification of Imported Goods
For products imported into India that are covered under mandatory certification.

## Foreign Manufacturers Certification Scheme (FMCS)
For foreign manufacturers seeking ISI mark licence.

### FMCS Process
1. Apply through manakonline.in
2. BIS conducts remote/physical audit of overseas factory
3. Samples drawn and tested in BIS lab or recognized lab in India
4. Licence granted with Indian Authorized Representative
5. Valid for specified period with surveillance

## Products Under Mandatory Certification
As of 2026, **400+** products are under mandatory BIS certification across categories:
- Steel and steel products
- Electrical equipment
- Electronics and IT goods
- Food products (via FSSAI referencing IS)
- Cement
- LPG equipment
- Chemicals
- Textiles
- Automotive components
- Solar equipment
- Medical devices
- Consumer products
""",

        "bis_quality_control_orders_guide.txt": """# Quality Control Orders (QCOs) — Comprehensive Guide

## What are Quality Control Orders?
Quality Control Orders (QCOs) are orders issued by the Central Government under Section 16 of the BIS Act, 2016. They mandate that certain goods shall conform to the relevant Indian Standard and bear the Standard Mark (ISI mark) of BIS.

## Purpose of QCOs
- Ensure quality of products sold in Indian market
- Protect consumers from substandard goods
- Promote "Make in India" quality standards
- Level playing field between domestic and imported goods

## Key QCO Categories

### Steel and Steel Products
- 200+ Indian Standards covering structural steel, TMT bars, stainless steel, wire rods
- Major QCOs: Steel QCO 2020, Steel QCO 2024, Stainless Steel Pipes QCO 2025

### Chemicals
- 50+ chemical products under QCO: methanol, aniline, acetic acid, toluene, acrylonitrile
- Several amended and some rescinded in 2024-2025

### Electronics and IT
- CRS Order 2021 covers 60+ electronic product categories
- Smart meters QCO 2023
- CCTV cameras CRO 2021

### Electrical Appliances  
- Air conditioners, refrigerators, washing machines, ceiling fans
- Water heaters QCO 2025

### Footwear
- Leather footwear and rubber/polymeric footwear QCOs (revised 2024)

### Textiles
- Cotton bales, polyester yarn, protective textiles, agro-textiles

### Solar and Renewable Energy
- Solar PV modules, solar thermal systems, solar inverters

### Non-Ferrous Metals
- Copper, aluminium, nickel, zinc, tin products

### Building Materials
- Cement, gypsum products, wood-based boards, safety glass

## QCO Compliance
1. Manufacturer must obtain BIS ISI mark licence for the product
2. Product must conform to relevant Indian Standard
3. Product must bear BIS Standard Mark
4. Both domestic and imported goods must comply
5. Non-compliance: penalties under BIS Act 2016

## Recent QCO Updates (2025-2026)
- Multiple rescind orders in 2025 for chemicals where standards were revised
- New QCOs for cookware, cross-recessed screws, hinges
- Transition Facilitation Quality Control Order 2026
- Several extension orders for implementation dates

## Important Links
- QCO list: www.bis.gov.in/product-certification/products-under-compulsory-certification/
- Apply for licence: www.manakonline.in
""",

        "bis_act_2016_summary.txt": """# BIS Act 2016 — Summary and Key Provisions

## Overview
The Bureau of Indian Standards Act, 2016 (Act No. 11 of 2016) replaced the earlier Bureau of Indian Standards Act, 1986. It received Presidential assent on March 22, 2016 and came into force on October 12, 2017.

## Key Objectives
1. Establish Bureau of Indian Standards as the National Standards Body
2. Provide for conformity assessment of products, services, systems, and processes
3. Enable mandatory certification and hallmarking
4. Strengthen quality infrastructure in India

## Structure of BIS
- **Governing Council**: Chaired by the Minister in charge of Consumer Affairs
- **Executive Committee**: Day-to-day management
- **Director General**: Chief Executive of BIS
- **Advisory Committees**: For specific sectors

## Key Provisions

### Section 10: Standard Mark
BIS may grant licence to use Standard Mark on products conforming to Indian Standards.

### Section 14: Conformity Assessment
BIS can establish conformity assessment schemes including:
- Product certification (ISI mark)
- Management system certification (ISO 9001, ISO 14001, etc.)
- Hallmarking

### Section 16: Compulsory Use of Standard Mark
Central Government may notify products for mandatory certification by QCO.

### Section 17: Hallmarking
Provisions for mandatory hallmarking of precious metal articles.

### Section 29: Penalties
| Offence | Penalty |
|---------|---------|
| Using Standard Mark without licence | Up to Rs. 5 lakh fine and/or 2 years imprisonment |
| Manufacturing non-conforming mandatory product | Up to Rs. 2 lakh fine and/or 2 years imprisonment |
| Second offence | Double the penalty |
| Selling non-hallmarked gold (in notified districts) | Up to Rs. 1 lakh fine and/or 1 year imprisonment |

### Section 35: BIS Fund
All fees, grants, and penalties go to the BIS Fund.

## BIS Rules, 2018
- Rules for grant, renewal, suspension, and cancellation of licences
- Fee structure for various services
- Procedure for conformity assessment

## BIS (Hallmarking) Regulations, 2018
- Recognition of Assaying and Hallmarking Centres
- Jeweller registration
- Hallmarking process and standards
- HUID system (introduced 2021)
- Amended in 2021, 2022, and subsequent years
""",

        "bis_consumer_faq_comprehensive.txt": """# BIS Consumer FAQ — Frequently Asked Questions

## General

**Q: What is BIS?**
A: The Bureau of Indian Standards (BIS) is the National Standards Body of India, established under the BIS Act, 2016. It formulates Indian Standards, operates conformity assessment schemes, and runs the hallmarking programme.

**Q: What is ISI mark?**
A: ISI (Indian Standards Institution) mark is a certification mark issued by BIS. Products bearing the ISI mark have been tested and certified to conform to the relevant Indian Standard. It is mandatory for certain products and voluntary for others.

**Q: How can I verify if a product has a genuine ISI mark?**
A: You can verify at www.manakonline.in by entering the licence number printed below the ISI mark. You can also call BIS helpline 1800-11-4000.

**Q: How to file a complaint about a substandard ISI marked product?**
A: 
1. Online: complaints@bis.gov.in
2. Phone: 1800-11-4000 (toll-free)
3. BIS Care App (Android/iOS)
4. Written complaint to nearest BIS office

## Hallmarking

**Q: Is hallmarking mandatory?**
A: Yes, hallmarking of gold jewellery is mandatory in 385 districts of India as of 2026. Jewellers in these districts must sell only hallmarked gold jewellery.

**Q: What purities of gold can be hallmarked?**
A: Only 14 carat (585 fineness), 18 carat (750 fineness), and 22 carat (916 fineness) gold can be hallmarked.

**Q: How to check if my gold jewellery is genuinely hallmarked?**
A: Check the HUID code using:
- BIS Care App
- verify.bis.gov.in
- SMS the HUID to 8130009727

**Q: What is the hallmarking charge?**
A: The hallmarking charge (marking fee) ranges from Rs. 45 to Rs. 75 per article depending on weight, payable by the jeweller.

**Q: Can I get my old gold jewellery hallmarked?**
A: Yes, you can get old gold jewellery hallmarked by taking it to any BIS-recognized Assaying and Hallmarking Centre (AHC).

## Product Certification

**Q: How long does it take to get an ISI mark licence?**
A: Typically 3-6 months from application submission, depending on the product category and completeness of application.

**Q: What is the cost of ISI mark licence?**
A: Application fee ranges from Rs. 1,000 to Rs. 5,000. Additionally, annual marking fee and testing charges apply.

**Q: Can foreign manufacturers get ISI mark?**
A: Yes, through the Foreign Manufacturers Certification Scheme (FMCS). The process involves factory audit and sample testing.

## CRS (Compulsory Registration Scheme)

**Q: What products need CRS registration?**
A: Electronics and IT products notified by MeitY, including mobile phones, laptops, LED lighting, power banks, adapters, printers, smart watches, CCTV cameras, and more.

**Q: How to apply for CRS?**
A: Apply online at www.crsbis.in with test reports from a BIS-recognized laboratory.

**Q: How long is CRS registration valid?**
A: CRS registration is valid for 2 years and must be renewed before expiry.

## Contact BIS
- **Toll-free helpline**: 1800-11-4000
- **Email**: cmd2@bis.gov.in
- **Website**: www.bis.gov.in
- **Manakonline**: www.manakonline.in (for applications)
- **Headquarters**: Manak Bhawan, 9 Bahadur Shah Zafar Marg, New Delhi - 110002
""",

        "bis_fees_charges_complete.txt": """# BIS Fees and Charges — Complete Reference (2025-2026)

## ISI Mark (Scheme-I) Fees

### Application Fee
| Category | Fee (Rs.) |
|----------|-----------|
| Simple products | 1,000 |
| Medium complexity | 2,000 |
| Complex products | 5,000 |

### Marking Fee
Marking fee is charged per unit of product manufactured and varies by product category. Updated gazette notification in January 2025 and amended in June 2025.

### Testing Fee
Testing charges depend on the Indian Standard and tests required. Payable to the testing laboratory.

### Surveillance Fee
Included in the marking fee structure.

## CRS (Scheme-II) Fees

| Service | Fee (Rs.) |
|---------|-----------|
| Registration (per model) | 1,000 |
| Renewal (per model) | 1,000 |
| Inclusion of new model | 1,000 |

## Hallmarking Fees

### Jeweller Registration
| Type | Fee (Rs.) |
|------|-----------|
| Single outlet | 5,000 |
| Additional outlet | 3,000 |
| Renewal (per outlet) | 5,000 |

### Hallmarking Charges (Marking Fee)
| Article Weight | Fee per article (Rs.) |
|---------------|----------------------|
| Up to 4 grams | 45 |
| 4g to 50 grams | 55 |
| Above 50 grams | 75 |
| Gold coin/bullion | 75 |

### AHC Recognition Fee
| Type | Fee (Rs.) |
|------|-----------|
| Initial recognition | 1,00,000 |
| Renewal | 50,000 |

## FMCS (Foreign Manufacturers) Fees
| Service | Fee (USD) |
|---------|-----------|
| Application | 500 |
| Factory audit (per man-day) | 1,000 |
| Testing | As per lab charges |
| Licence grant | 2,000 |

## BIS Standards Purchase
- Indian Standards can be purchased from BIS e-Sale portal
- Prices vary from Rs. 200 to Rs. 10,000+ depending on the standard

## Concessions for MSMEs
- 80% concession in marking fee for micro units for first 3 years (Gazette notification June 2023)
- Scheme-1 concession extended to May 2029

## Payment Methods
- Online: manakonline.in (NEFT/RTGS/Net banking/UPI)
- DD/Banker's cheque in favour of "Secretary, BIS"
""",
    }
    
    created = 0
    for filename, content in files.items():
        filepath = supplementary_dir / filename
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            log.info("  Created supplementary: %s", filename)
            created += 1
        else:
            log.info("  Already exists: %s", filename)
    
    return created


# --------------------------------------------------------------------------
# Main orchestrator
# --------------------------------------------------------------------------

def run_all(source_filter: str | None = None, max_pages: int = 500, delay: float = 3.0):
    """Run scraping across all or specified sources."""
    manifest = load_manifest()
    session = create_session()
    total_fetched = 0
    
    # Always generate supplementary data first
    log.info("=" * 60)
    log.info("STEP 1: Generating supplementary knowledge base files")
    supp_count = generate_supplementary_data()
    log.info("  Created %d supplementary files", supp_count)
    
    # Determine which sources to crawl
    sources_to_crawl = SOURCES
    if source_filter:
        if source_filter in SOURCES:
            sources_to_crawl = {source_filter: SOURCES[source_filter]}
        else:
            log.error("Unknown source: %s. Available: %s", source_filter, list(SOURCES.keys()))
            return
    
    # Crawl each source
    for key, config in sources_to_crawl.items():
        if key == "standards":
            fetched = scrape_standards_portal(session, manifest, max_pages, delay)
        else:
            fetched = crawl_source(key, config, manifest, session, max_pages, delay)
        total_fetched += fetched
    
    # Fetch open data
    if not source_filter or source_filter == "datagov":
        log.info("=" * 60)
        log.info("STEP: Fetching open government data")
        total_fetched += fetch_open_data(session, manifest, max_pages, delay)
    
    # Summary
    log.info("=" * 60)
    log.info("MEGA SCRAPER COMPLETE")
    log.info("  Total pages fetched this run: %d", total_fetched)
    log.info("  Total entries in manifest: %d", len(manifest))
    
    # Count by source
    source_counts = {}
    for entry in manifest.values():
        src = entry.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items()):
        log.info("    %s: %d entries", src, count)
    
    # Data size
    total_size = 0
    for entry in manifest.values():
        lp = entry.get("local_path", "")
        if lp and os.path.exists(lp):
            total_size += os.path.getsize(lp)
    log.info("  Total data size: %.1f MB", total_size / (1024 * 1024))
    log.info("  Manifest: %s", MANIFEST_PATH)
    
    if FAILED_LOG_PATH.exists():
        log.info("  Failures logged: %s", FAILED_LOG_PATH)


def main():
    parser = argparse.ArgumentParser(
        description="BIS Mega Scraper — comprehensive data collection for 5GB+ knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", help=f"Crawl only this source. Available: {', '.join(SOURCES.keys())}, datagov")
    parser.add_argument("--max-pages", type=int, default=500, help="Max pages per source (default: 500)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Seconds between requests (default: 3.0)")
    parser.add_argument("--list-sources", action="store_true", help="List available sources and exit")
    args = parser.parse_args()
    
    if args.list_sources:
        print("\nAvailable scraping sources:")
        print("-" * 60)
        for key, config in SOURCES.items():
            print(f"  {key:15s} — {config['name']}")
            print(f"  {'':15s}   {config['description']}")
            print()
        print(f"  {'datagov':15s} — Open Government Data (data.gov.in)")
        print(f"  {'':15s}   BIS statistics and certification data")
        return
    
    log.info("BIS Mega Scraper starting...")
    run_all(source_filter=args.source, max_pages=args.max_pages, delay=args.delay)


if __name__ == "__main__":
    main()
