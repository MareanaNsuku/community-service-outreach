#!/usr/bin/env python3
"""scraper_v3.py — SerpAPI-powered NPO discovery. Never produces garbage."""
import os, re, sys, time, json
from urllib.parse import urlparse
import requests
import pandas as pd

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SERPAPI_URL = "https://serpapi.com/search.json"

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Domains that are NEVER real NPO contacts
JUNK_DOMAINS = {
    "wikipedia.org", "wikimedia.org", "youtube.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "linkedin.com", "tiktok.com",
    "pinterest.com", "reddit.com", "quora.com", "medium.com", "blogspot.com",
    "wordpress.com", "wordpress.org", "wixsite.com", "wix.com",
    "merriam-webster.com", "dictionary.com", "britannica.com",
    "amazon.com", "amazon.fr", "amazon.co.uk", "ebay.com", "etsy.com",
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
    "scribd.com", "issuu.com", "slideshare.net", "yumpu.com",
    "gov.za", "gov.uk", "gov.za.com",   # skip govt (mostly)
    "novaskin.me", "minecraft.net", "curseforge.com",
    "highonfilms.com", "imdb.com", "rottentomatoes.com",
    "mospi.gov.in",  # India govt stats
}

# Domains that indicate a legit SA NPO or directory
GOOD_TLDS = (".co.za", ".org.za", ".org", ".co", ".africa", ".ngo", ".net")

BAD_EMAIL_PARTS = [
    "noreply", "no-reply", "donotreply", "postmaster", "abuse@",
    "webmaster", "wordpress", "wixpress", "sentry", "test@",
    "example@", "user@", "name@", "email@", "info@example",
    "bug-reporting", "@m-w.com", "@w3.org", "@schema.org",
]

def is_junk_domain(url):
    if not url: return True
    try:
        host = urlparse(url).netloc.lower()
        return any(d in host for d in JUNK_DOMAINS)
    except: return True

def is_good_email(email):
    e = email.lower().strip()
    if len(e) < 6 or "@" not in e: return False
    if any(bad in e for bad in BAD_EMAIL_PARTS): return False
    # Reject non-email patterns
    if e.startswith("wght") or ".." in e: return False
    if re.search(r'[0-9a-f]{20,}@', e): return False   # long hex hashes
    return True

def extract_emails(text):
    return [e for e in set(EMAIL_REGEX.findall(text or "")) if is_good_email(e)]

def serpapi_search(query):
    """Return list of {url, title, snippet} from Google."""
    if not SERPAPI_KEY:
        print("❌ SERPAPI_KEY not set")
        return []
    try:
        r = requests.get(SERPAPI_URL, params={
            "q": query, "api_key": SERPAPI_KEY, "num": 20, "gl": "za", "hl": "en"
        }, timeout=30)
        if r.status_code != 200:
            print(f"   SerpAPI HTTP {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "displayed_link": item.get("displayed_link", ""),
            })
        return results
    except Exception as e:
        print(f"   SerpAPI error: {e}")
        return []

def is_npo_result(title, snippet, url):
    """Heuristic: is this an NPO result, not a news/blog/dict page?"""
    if is_junk_domain(url): return False
    text = (title + " " + snippet).lower()
    # Require at least one NPO signal
    signals = [
        "npo", "ngo", "non-profit", "nonprofit", "non profit",
        "charity", "community", "trust", "foundation", "organisation",
        "organization", "volunteer", "outreach", "welfare", "development",
    ]
    return any(s in text for s in signals)

def scrape(city, category):
    queries = [
        f"{category} {city} site:.org.za",
        f"{category} {city} site:.co.za NPO",
        f"{category} non-profit {city} contact",
        f"{city} {category} NGO contact email",
    ]
    results = {}
    for q in queries:
        print(f"  Query: {q}")
        for r in serpapi_search(q):
            if not r["url"]: continue
            if is_junk_domain(r["url"]): continue
            if not is_npo_result(r["title"], r["snippet"], r["url"]): continue
            if r["url"] not in results:
                results[r["url"]] = r
        time.sleep(0.5)
    print(f"  Filtered to {len(results)} plausible NPO URLs")

    rows = []
    for url, r in results.items():
        emails = extract_emails(r["snippet"])
        # If no email in snippet, fetch pages & scan mailto: links
        if not emails:
            p = urlparse(url)
            base = f"{p.scheme}://{p.netloc}"
            paths = ["", "/contact", "/contact-us", "/about", "/about-us",
                     "/team", "/our-team", "/get-in-touch", "/reach-us"]
            found = set()
            for path in paths:
                full = base + path
                try:
                    resp = requests.get(full, timeout=8, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; ContactBot/1.0)"
                    })
                    if resp.status_code != 200:
                        continue
                    html = resp.text[:80000]
                    # mailto: links
                    for m in re.findall(r'mailto:([^"\'<>?\s]+)', html, re.I):
                        if is_good_email(m):
                            found.add(m.lower())
                    # Plain-text emails
                    for e in extract_emails(html):
                        found.add(e.lower())
                    if found: break
                    time.sleep(0.3)
                except: pass
            emails = list(found)

        # Name from title or domain
        name = re.sub(r"\s*[|–-]\s*.*$", "", r["title"]).strip() or urlparse(url).netloc
        if not emails:
            continue
        for e in emails[:2]:  # max 2 emails per org
            rows.append({
                "Organisation Name": name,
                "Category": category,
                "Location": city,
                "Email": e.lower(),
                "Website": url,
                "Source": "serpapi_v3",
            })

    return rows

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scraper_v3.py <city> <category>")
        sys.exit(1)
    city, category = sys.argv[1], sys.argv[2]
    print(f"🔍 v3 Scrape: {category} in {city}")
    rows = scrape(city, category)
    if not rows:
        print("❌ No contacts found")
        sys.exit(1)

    os.makedirs("results", exist_ok=True)
    sc = city.replace(" ", "_")
    sg = category.replace(" ", "_").replace("&","and")
    out = f"results/scraped_{sc}_{sg}.xlsx"
    df = pd.DataFrame(rows).drop_duplicates("Email")
    df.to_excel(out, index=False)
    print(f"✅ Saved {len(df)} contacts → {out}")
