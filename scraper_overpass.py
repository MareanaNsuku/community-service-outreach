#!/usr/bin/env python3
"""Overpass API scraper — free, unlimited, NPO-focused."""
import os, re, sys, time, json
from urllib.parse import urlparse, quote
import requests
import pandas as pd

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

BAD_LOCAL = ["@xyz.com","@example.com","@domain.com","@test.com","@foo.com",
             "@stanford.edu","@harvard.edu","@mit.edu",
             "noreply","no-reply","donotreply","postmaster","webmaster",
             "abuse","feedback","press","jobs","hr","careers","vacancies",
             "sentry","wixpress","example","test@","info@example",
             "you@email","your@email","user@example","name@example",
             "bootstrap","fontawesome","jquery","rspack","core-js","slick-carousel"]
BAD_DOMAINS = ["facebook.com","instagram.com","twitter.com","youtube.com",
               "linkedin.com","wikipedia.org","quora.com","reddit.com",
               "tripadvisor","yelp","booking.com","quicket","gov.za",
               "merriam","amazon.","ebay.","justice.gov"]

# Suburb centres + radius (metres)
LOCATIONS = {
    "Mowbray":    (-33.9456, 18.4686, 1800),
    "Rondebosch": (-33.9630, 18.4720, 1800),
}

# OSM tags to search — broad NPO/community types
OSM_QUERIES = [
    ('amenity', 'school'),
    ('amenity', 'community_centre'),
    ('amenity', 'library'),
    ('amenity', 'social_facility'),
    ('amenity', 'place_of_worship'),
    ('amenity', 'kindergarten'),
    ('amenity', 'arts_centre'),
    ('amenity', 'theatre'),
    ('amenity', 'clinic'),
    ('amenity', 'hospital'),
    ('office', 'ngo'),
    ('office', 'charity'),
    ('office', 'association'),
    ('office', 'foundation'),
    ('office', 'educational_institution'),
    ('amenity', 'veterinary'),
    ('amenity', 'animal_shelter'),
    ('leisure', 'sports_centre'),
    ('leisure', 'park'),
    ('tourism', 'museum'),
]

def ok_email(e):
    e = e.lower().strip()
    if "@" not in e or len(e) < 6 or len(e) > 70: return False
    if any(b in e for b in BAD_LOCAL): return False
    if re.search(r'@\d+\.\d+', e): return False
    if any(c in e for c in ["&", '"', "'", "<", ">", ";", "&quot;"]): return False
    if e.endswith((".png",".jpg",".gif",".css",".js",".svg")): return False
    domain = e.split("@")[1]
    if "." not in domain or len(domain.split(".")[-1]) < 2: return False
    return True

MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {
    "User-Agent": "NPO-Outreach/1.0 (educational project; mrnnsu001@myuct.ac.za)",
    "Accept": "*/*",
}

def overpass_query(lat, lon, radius, tag_key, tag_val):
    """Try each Overpass mirror until one works."""
    q = f"""
    [out:json][timeout:30];
    (
      node["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
      way["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
    );
    out body;
    """
    for url in MIRRORS:
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                return r.json().get("elements", [])
        except Exception as e:
            continue
    print(f"  all mirrors failed")
    return []

def emails_from_site(url, timeout=8):
    if not url or not url.startswith("http"): return []
    try:
        p = urlparse(url)
        if any(b in p.netloc.lower() for b in BAD_DOMAINS): return []
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

def scrape_suburb(suburb, lat, lon, radius, category):
    """Scrape one suburb for one category."""
    print(f"🔍 {suburb} — {category}")
    all_places = {}
    for tag_key, tag_val in OSM_QUERIES:
        places = overpass_query(lat, lon, radius, tag_key, tag_val)
        for p in places:
            pid = p.get("id")
            if pid in all_places: continue
            tags = p.get("tags", {})
            if not tags: continue
            # Only keep NPO-ish
            name = tags.get("name", "").strip()
            if not name: continue
            all_places[pid] = {
                "name": name,
                "website": tags.get("website", "") or tags.get("contact:website",""),
                "email": tags.get("email", "") or tags.get("contact:email",""),
                "phone": tags.get("phone", "") or tags.get("contact:phone",""),
                "address": tags.get("addr:street",""),
                "category": tag_val,
            }
        time.sleep(0.5)  # be nice to Overpass

    print(f"  → {len(all_places)} places in {suburb}")
    rows = []
    for pid, p in all_places.items():
        emails = []
        # 1. Direct email in OSM tags
        if p["email"] and ok_email(p["email"]):
            emails.append(p["email"].lower())
        # 2. Fallback: scrape website
        if not emails and p["website"]:
            emails = emails_from_site(p["website"])
        if not emails:
            print(f"  – {p['name']} — no email")
            continue
        for e in emails:
            rows.append({
                "Organisation Name": p["name"],
                "Category": category,
                "Location": suburb,
                "Email": e,
                "Phone": p["phone"],
                "Website": p["website"],
            })
        print(f"  ✅ {p['name']} → {emails[0]}")
    return rows

def main():
    if len(sys.argv) < 3:
        print("Usage: scraper_overpass.py <suburb> <category>"); sys.exit(1)
    suburb, category = sys.argv[1], sys.argv[2]

    if suburb not in LOCATIONS:
        print(f"❌ Unknown suburb. Use: {list(LOCATIONS.keys())}"); sys.exit(1)

    lat, lon, radius = LOCATIONS[suburb]
    rows = scrape_suburb(suburb, lat, lon, radius, category)

    if not rows:
        print("  no emails"); sys.exit(0)

    os.makedirs("results", exist_ok=True)
    sc = suburb.replace(" ", "_")
    sg = category.replace(" ", "_").replace("&","and")
    out = f"results/scraped_{sc}_{sg}.xlsx"
    pd.DataFrame(rows).drop_duplicates("Email").to_excel(out, index=False)
    print(f"✅ {len(rows)} saved → {out}")

if __name__ == "__main__":
    main()
