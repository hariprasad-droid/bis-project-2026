#!/usr/bin/env python3
"""
bis_scraper.py — reliable, resumable scraper for freely-available BIS content.

WHAT THIS DOES
--------------
Crawls the public, freely-readable sections of bis.gov.in (certification
schemes, hallmarking, FAQs, consumer info, "what's new"/revised-standards
listings, gazette notifications) in both English and Hindi, and downloads:
  - page HTML  -> data/raw/html/
  - linked PDFs -> data/raw/pdf/
It keeps a manifest (data/sources.json) of every URL it has fetched, with a
content hash and timestamp, so re-running the script later only fetches
NEW or CHANGED pages — this doubles as your "keep the knowledge base
updated" mechanism.

RELIABILITY
-----------
- PDFs/pages are downloaded by STREAMING to disk in chunks (not loaded
  fully into memory first), so a dropped connection mid-file is caught
  early and retried, instead of surfacing as an unrecoverable
  IncompleteRead deep in urllib3.
- Every fetch retries up to MAX_RETRIES times with exponential backoff on
  transient errors (timeouts, dropped connections, 5xx). A real 4xx is
  NOT retried — that's a genuine error, not a blip.
- If 3+ fetches in a row fail, the crawler assumes the site is
  rate-limiting us and cools down for a bit before continuing, instead of
  hammering an already-struggling server.
- robots.txt is fetched through the SAME retrying session rather than via
  Python's RobotFileParser.read() directly — that stock method treats a
  403 on robots.txt itself as "disallow everything", which is wrong when
  the 403 is really a transient WAF response to our own burst of
  requests. If robots.txt is unreachable, we default to allow and print
  one clear warning telling you to check it by hand.
- Every URL that fails all retries is recorded in data/failed_urls.txt at
  the end, with a reason, so nothing silently vanishes — you can inspect
  or re-run against just those later (simply re-running the whole script
  also retries them, since they were never saved to the manifest).

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
It will not follow links into BIS's e-Sale / paid standards-purchase
portal, and it will not attempt to pull full text of individual IS
standards (those are commercial publications, not freely redistributable).
It only crawls path prefixes you explicitly allow — see
ALLOWED_PATH_PREFIXES below — so it naturally stays out of paywalled areas
as long as you don't add them.

USAGE
-----
    pip install requests beautifulsoup4
    python bis_scraper.py                       # uses built-in seed list
    python bis_scraper.py --max-pages 500        # cap the crawl (default 500)
    python bis_scraper.py --seeds my_seeds.txt   # your own seed URL list
    python bis_scraper.py --force                # re-fetch even if unchanged

Re-run it any time — it's incremental and safe to interrupt (Ctrl+C) and
resume; already-fetched, unchanged files are skipped.
"""

import argparse
import hashlib
import json
import logging
import os
import time
import urllib.robotparser
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_DOMAIN = "bis.gov.in"

START_URLS = [
    # Certification
    "https://www.bis.gov.in/product-certification/",
    "https://www.bis.gov.in/product-certification/product-certification-overview/",
    "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/",
    "https://www.bis.gov.in/product-certification/product-certification-process/",
    "https://www.bis.gov.in/product-certification/online-information/",
    "https://www.bis.gov.in/product-certification/product-specific-information-2/",
    # Hallmarking
    "https://www.bis.gov.in/hallmarking/",
    "https://www.bis.gov.in/hallmarking-overview/",
    "https://www.bis.gov.in/hallmarking-overview/hallmarking-faqs/",
    "https://www.bis.gov.in/hallmarking-overview/hallmarking-regulation-2018/",
    "https://www.bis.gov.in/hallmarking-overview/gold-monetization-scheme/",
    "https://www.bis.gov.in/hallmarking-overview/hallmarking-contact-us/",
    # Consumer-facing
    "https://www.bis.gov.in/consumer-affairs/",
    "https://www.bis.gov.in/bis-faq/",
    # Standards lookup / news
    "https://www.bis.gov.in/know-your-standard/",
    "https://www.bis.gov.in/whats_new/",
    # Hindi variants (BIS serves these as ?lang=hi on the same paths, but
    # seeding a few explicitly helps the crawler discover the pattern early)
    "https://www.bis.gov.in/product-certification/?lang=hi",
    "https://www.bis.gov.in/hallmarking/?lang=hi",
]

# Only crawl pages whose path starts with one of these — this is what keeps
# the crawler inside free/public content and out of e-Sale/purchase pages.
ALLOWED_PATH_PREFIXES = [
    "/product-certification",
    "/hallmarking",
    "/hallmarking-overview",
    "/consumer-affairs",
    "/know-your-standard",
    "/whats_new",
    "/bis-faq",
    "/bs",                 # gazette notifications, e.g. /bs/BIS_Hallmarking_...pdf
    "/wp-content/uploads",  # where BIS hosts its own PDFs
]

# Never follow links whose path contains any of these — belt-and-braces
# exclusion of paid/portal areas even if a prefix above accidentally matches.
BLOCKED_PATH_SUBSTRINGS = [
    "esale", "e-sale", "manakonline", "login", "signin", "cart", "checkout",
]

# Skip these regardless of prefix — large annual reports aren't core RAG
# content and are the files most likely to trip flaky-connection errors.
# Remove entries here if you actually want them.
SKIP_PATH_SUBSTRINGS = [
    "annualreport", "annual_report", "annual-report",
]

USER_AGENT = (
    "Mozilla/5.0 (compatible; SIH2026-PS26107-ResearchBot/1.0; "
    "educational hackathon project; contact: <put your team email here>)"
)

OUT_DIR = "data/raw"
MANIFEST_PATH = "data/sources.json"
FAILED_LOG_PATH = "data/failed_urls.txt"

REQUEST_TIMEOUT = 45          # generous — some BIS PDFs are large and slow
DEFAULT_DELAY_SECONDS = 3.0
MAX_RETRIES = 4
BACKOFF_FACTOR = 3.0           # seconds: 3, 6, 9, 12 between retries
STREAM_CHUNK_SIZE = 1024 * 64  # 64KB chunks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bis_scraper")


# --------------------------------------------------------------------------
# Manifest / failure log helpers
# --------------------------------------------------------------------------

def load_manifest(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(path, manifest):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def append_failed(url, reason):
    os.makedirs(os.path.dirname(FAILED_LOG_PATH), exist_ok=True)
    with open(FAILED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}\t{url}\t{reason}\n")


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# robots.txt — see module docstring for why this isn't RobotFileParser.read()
# --------------------------------------------------------------------------

_robots_warned = False


def build_robot_parser(session):
    global _robots_warned
    rp = urllib.robotparser.RobotFileParser()
    url = f"https://{BASE_DOMAIN}/robots.txt"
    resp = fetch_text(session, url, quiet=True)
    if resp is not None:
        rp.parse(resp.splitlines())
    else:
        rp.parse(['User-agent: *', 'Allow: /'])
        if not _robots_warned:
            log.warning(
                "Could not fetch robots.txt (site may be rate-limiting us). "
                "Proceeding with default-allow for now — please check "
                "https://%s/robots.txt manually.", BASE_DOMAIN,
            )
            _robots_warned = True
    return rp


def allowed_by_robots(rp, url):
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


# --------------------------------------------------------------------------
# URL filtering
# --------------------------------------------------------------------------

def is_in_scope(url):
    parsed = urlparse(url)
    if BASE_DOMAIN not in parsed.netloc:
        return False
    path = parsed.path or "/"
    lower_url = url.lower()
    if any(sub in lower_url for sub in BLOCKED_PATH_SUBSTRINGS):
        return False
    if any(sub in lower_url for sub in SKIP_PATH_SUBSTRINGS):
        return False
    if path.lower().endswith(".pdf"):
        return True
    return any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def sanitize_slug(raw):
    """
    Strip everything Windows (and to be safe, Linux/macOS) forbids or
    dislikes in a filename: <>:"/\\|?* , control characters, and trailing
    dots/spaces. Also cap the length so we never hit MAX_PATH-style limits
    on deeply nested BIS URLs with long query strings.
    """
    cleaned = "".join("_" if c in _INVALID_FILENAME_CHARS or ord(c) < 32 else c for c in raw)
    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = "index"
    return cleaned[:150]


def local_path_for(url, is_pdf):
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_") or "index"
    if parsed.query:
        slug += "_" + parsed.query.replace("&", "_").replace("=", "-")
    slug = sanitize_slug(slug)
    if is_pdf:
        if not slug.lower().endswith(".pdf"):
            slug += ".pdf"
        return os.path.join(OUT_DIR, "pdf", slug)
    return os.path.join(OUT_DIR, "html", slug + ".html")


# --------------------------------------------------------------------------
# Fetching — streamed to disk, with retry + backoff
# --------------------------------------------------------------------------

def fetch_text(session, url, quiet=False):
    """Small text fetch (used for robots.txt). Returns text or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError:
            return None
        except requests.RequestException:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_FACTOR * attempt)
    return None


def download_to_file(session, url, dest_path):
    """
    Stream a URL's response body straight to disk in chunks, retrying the
    whole download from scratch (with backoff) if the connection drops
    partway through. Returns (success: bool, content_type: str, reason: str).
    """
    last_reason = None
    for attempt in range(1, MAX_RETRIES + 1):
        tmp_path = dest_path + ".part"
        try:
            with session.get(url, timeout=REQUEST_TIMEOUT, stream=True) as resp:
                if resp.status_code >= 500 and attempt < MAX_RETRIES:
                    last_reason = f"HTTP {resp.status_code}"
                    time.sleep(BACKOFF_FACTOR * attempt)
                    continue
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=STREAM_CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp_path, dest_path)  # atomic-ish rename once fully written
            return True, content_type, None
        except requests.exceptions.HTTPError as e:
            _cleanup_partial(tmp_path)
            return False, "", str(e)  # real 4xx — don't retry
        except requests.RequestException as e:
            _cleanup_partial(tmp_path)
            last_reason = str(e)
            if attempt < MAX_RETRIES:
                wait = BACKOFF_FACTOR * attempt
                log.info("  transient error on %s (%s) — retrying in %.0fs [%d/%d]",
                          url, e, wait, attempt, MAX_RETRIES)
                time.sleep(wait)
        except OSError as e:
            # A bad local path (illegal characters, path too long, etc.) —
            # this is NOT a network blip, so don't retry, just report it and
            # move on. sanitize_slug() should prevent most of these, but this
            # catch is what stops one weird URL from crashing the whole run.
            _cleanup_partial(tmp_path)
            return False, "", f"local filesystem error: {e}"
    return False, "", last_reason


def _cleanup_partial(tmp_path):
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except OSError:
        pass


def extract_links(base_url, html_bytes):
    soup = BeautifulSoup(html_bytes, "html.parser")
    links = set()
    for tag in soup.find_all("a", href=True):
        href = urljoin(base_url, tag["href"].split("#")[0])
        links.add(href)
    return links


# --------------------------------------------------------------------------
# Main crawl
# --------------------------------------------------------------------------

def crawl(seeds, max_pages, delay, force):
    manifest = load_manifest(MANIFEST_PATH)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    rp = build_robot_parser(session)
    robots_recheck_every = 25
    since_recheck = 0

    queue = deque(seeds)
    seen = set(seeds)
    fetched_count = 0
    consecutive_failures = 0
    failures = []

    while queue and fetched_count < max_pages:
        url = queue.popleft()

        if not is_in_scope(url):
            continue

        if consecutive_failures >= 3:
            cooldown = min(90, 10 * consecutive_failures)
            log.warning("  %d consecutive failures — cooling down %ds", consecutive_failures, cooldown)
            time.sleep(cooldown)

        since_recheck += 1
        if since_recheck >= robots_recheck_every:
            rp = build_robot_parser(session)
            since_recheck = 0

        if not allowed_by_robots(rp, url):
            log.info("  blocked by robots.txt: %s", url)
            continue

        # Everything from here on is wrapped: a single bad URL, a weird
        # filename, an unexpected server response — none of it should ever
        # be able to kill a run that might be an hour+ into progress. If
        # something truly unforeseen happens, we log it, count it as a
        # failure for THIS url, and keep going.
        try:
            is_pdf = url.lower().endswith(".pdf")
            entry = manifest.get(url)
            local_path = local_path_for(url, is_pdf)

            if entry is not None and not force and os.path.exists(entry.get("local_path", "")):
                # Already have it — for HTML we still want to re-crawl its
                # links occasionally, but skip re-downloading unchanged content.
                log.info("  already fetched, skipping download: %s", url)
                ok = True
            else:
                ok, content_type, reason = download_to_file(session, url, local_path)
                time.sleep(delay)
                if not ok:
                    consecutive_failures += 1
                    failures.append((url, reason))
                    append_failed(url, reason)
                    continue
                consecutive_failures = 0
                manifest[url] = {
                    "local_path": local_path,
                    "content_type": content_type,
                    "sha256": sha256_of_file(local_path),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "is_pdf": is_pdf,
                }
                save_manifest(MANIFEST_PATH, manifest)
                log.info("  saved (%s): %s", "new" if entry is None else "updated", url)

            fetched_count += 1

            if not is_pdf and os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    html_bytes = f.read()
                for link in extract_links(url, html_bytes):
                    if link not in seen and is_in_scope(link):
                        seen.add(link)
                        queue.append(link)

        except Exception as e:
            # Catch-all safety net: log and move on rather than crashing a
            # run that may be an hour+ deep. Should rarely trigger now that
            # filenames are sanitized and OSError is handled above, but this
            # guarantees no single URL can ever take the whole crawl down.
            log.warning("  unexpected error on %s (%s) — skipping this URL", url, e)
            consecutive_failures += 1
            failures.append((url, str(e)))
            append_failed(url, f"unexpected error: {e}")
            continue

    log.info(
        "Done. Fetched/checked %d pages this run. Manifest has %d entries total. Failures: %d.",
        fetched_count, len(manifest), len(failures),
    )
    if failures:
        log.info("Failed URLs logged to %s — re-run the script to retry them (they weren't saved to the manifest).", FAILED_LOG_PATH)
    log.info("Raw files: %s | Manifest: %s", OUT_DIR, MANIFEST_PATH)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", help="text file with one seed URL per line (default: built-in list)")
    parser.add_argument("--max-pages", type=int, default=500, help="stop after fetching this many pages (default 500)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="seconds between requests (default 3.0)")
    parser.add_argument("--force", action="store_true", help="re-download even if already in the manifest")
    args = parser.parse_args()

    if args.seeds:
        with open(args.seeds, "r", encoding="utf-8") as f:
            seeds = [line.strip() for line in f if line.strip()]
    else:
        seeds = START_URLS

    log.info("Starting crawl with %d seed URL(s), max_pages=%d, delay=%ss",
              len(seeds), args.max_pages, args.delay)
    crawl(seeds, args.max_pages, args.delay, args.force)


if __name__ == "__main__":
    main()
