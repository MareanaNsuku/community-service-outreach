#!/usr/bin/env python3
"""Google Maps scraper via SerpAPI."""
import os, re, sys, time
from urllib.parse import urlparse
import requests
import pandas as pd

KEY = os.getenv("SERPAPI_KEY", "")
if not KEY:
    print("❌ SERPAPI_KEY not set"); sys.exit(0)

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
BAD_LOCAL = ["noreply","no-reply","donotreply","postmaster","webmaster",
             "abuse","feedback","press","jobs","hr","careers","vacancies",
             "sentry","wixpress","example","test@","info@example",
             "you@email","your@email","user@example","name@example",
             "someone@example","email@example","sample@","placeholder@"]
BAD_DOMAINS = ["facebook.com","instagram.com","twitter.com","youtube.com",
               "linkedin.com","wikipedia.org","quora.com","reddit.com",
               "medium.com","tripadvisor","yelp","booking.com","quicket",
               "gov.za","merriam","amazon.","ebay."]

def junk(d): return any(b in d.lower() for b in BAD_DOMAINS)

def ok_email(e):
    e = e.lower().strip()
    if "@" not in e or len(e) < 6 or len(e) > 70: return False
    if any(b in e for b in BAD_LOCAL): return False
    if e.endswith((".png",".jpg",".gif",".css",".js",".svg")): return False
    return True

def maps(query):
    try:
        r = requests.get("https://serpapi.com/search.json", params={
            "engine":"google_maps","q":query,"type":"search",
            "gl":"za","hl":"en","api_key":KEY,
        }, timeout=40)
        if r.status_code != 200:
            print(f"  maps HTTP {r.status_code}"); return []
        return r.json().get("local_results", [])
    except Exception as e:
        print(f"  maps err: {e}"); return []

def emails_from_site(url, timeout=8):
    if not url or not url.startswith("http"): return []
    try:
        p = urlparse(url)
        if junk(p.netloc): return []
    except: return []
    base = f"{p.scheme}://{p.netloc}"
    found = set()
    for path in ["", "/contact", "/contact-us", "/about", "/about-us"]:
        try:
            r = requests.get(base+path, timeout=timeout,
                headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200: continue
            html = r.text[:120000]
            for m in re.findall(r'mailto:([^"\'<>\s?]+)', html, re.I):
                m = m.lower().strip()
                if ok_email(m): found.add(m)
            for e in EMAIL_RE.findall(html):
                e = e.lower().strip()
                if ok_email(e): found.add(e)
            if found: break
            time.sleep(0.3)
        except: pass
    return sorted(found, key=len)[:2]

def main():
    if len(sys.argv) < 3:
        print("Usage: scraper_maps.py <city> <category>"); sys.exit(1)
    city, category = sys.argv[1], sys.argv[2]

    print(f"🔍 Maps: {category} in {city}")
    places = maps(f"{category} {city} NPO")
    print(f"  → {len(places)} places")
    if not places: sys.exit(0)

    rows, seen = [], set()
    for p in places[:25]:
        name = p.get("title","").strip()
        site = p.get("website","")
        if not name or name.lower() in seen: continue
        seen.add(name.lower())
        emails = emails_from_site(site) if site else []
        if emails:
            for e in emails:
                rows.append({
                    "Organisation Name": name,
                    "Category": category,
                    "Location": city,
                    "Email": e,
                    "Phone": p.get("phone",""),
                    "Website": site,
                })
            print(f"  ✅ {name} → {emails[0]}")
        else:
            print(f"  – {name}")

    if not rows:
        print("  no emails"); sys.exit(0)

    os.makedirs("results", exist_ok=True)
    sc = city.replace(" ", "_")
    sg = category.replace(" ", "_").replace("&","and")
    out = f"results/scraped_{sc}_{sg}.xlsx"
    pd.DataFrame(rows).drop_duplicates("Email").to_excel(out, index=False)
    print(f"✅ {len(rows)} saved → {out}")

if __name__ == "__main__":
    main()
