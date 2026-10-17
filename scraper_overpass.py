#!/usr/bin/env python3
"""Category-aware Overpass scraper — strict location, no healthcare, no wrong suburbs."""
import os, re, sys, time
from urllib.parse import urlparse
import requests
import pandas as pd

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# TIGHT radius (900m) — stays inside suburb
LOCATIONS = {
    "Mowbray":    (-33.9456, 18.4686, 900),
    "Rondebosch": (-33.9630, 18.4720, 900),
}

# Category → OSM tag pairs (NO healthcare tags)
CATEGORY_TAGS = {
    "Community Development": [('amenity','community_centre'),('office','ngo'),('office','charity'),('office','foundation')],
    "Youth Development": [('amenity','youth_centre'),('amenity','school'),('amenity','kindergarten'),('office','educational_institution')],
    "Youth & Tutoring": [('amenity','school'),('amenity','kindergarten'),('office','educational_institution')],
    "Mentorship Programmes": [('amenity','youth_centre'),('office','ngo'),('office','foundation')],
    "Adult Literacy": [('amenity','library'),('office','educational_institution')],
    "Skills Development": [('office','educational_institution'),('amenity','college')],
    "Early Childhood Development": [('amenity','kindergarten'),('amenity','childcare')],
    "Arts & Culture": [('amenity','arts_centre'),('amenity','theatre'),('tourism','museum'),('tourism','gallery')],
    "Museums & Heritage": [('tourism','museum')],
    "Sports & Recreation": [('leisure','sports_centre'),('club','sport')],
    "Sports Clubs": [('club','sport'),('leisure','sports_centre')],
    "Animal Welfare": [('amenity','animal_shelter')],
    "Environmental": [('office','ngo'),('leisure','garden')],
    "Food Security": [('amenity','social_facility'),('shop','charity')],
    "Homeless Shelters": [('amenity','social_facility'),('social_facility','shelter')],
    "Child Welfare": [('amenity','social_facility'),('social_facility','group_home')],
    "Religious Charities": [('amenity','place_of_worship')],
    "Interfaith Organisations": [('amenity','place_of_worship')],
    "Libraries & Reading Programmes": [('amenity','library')],
    "Volunteer Centres & NGO Support": [('office','ngo'),('office','charity'),('office','association')],
    "Community Centres": [('amenity','community_centre')],
    "Public Parks & Gardens": [('leisure','park'),('leisure','garden')],
}

BAD_LOCAL = ["noreply","no-reply","donotreply","postmaster","webmaster",
             "abuse","feedback","press","jobs","hr","careers","vacancies",
             "sentry","wixpress","bootstrap","fontawesome","jquery",
             "rspack","core-js","slick-carousel","latofonts","typekit",
             "googleapis","gstatic","cdn","fonts","adobe","netcare"]
BAD_DOMAINS = ["facebook.com","instagram.com","twitter.com","youtube.com",
               "linkedin.com","wikipedia.org","quora.com","reddit.com",
               "tripadvisor","yelp","booking.com","quicket","gov.za",
               "merriam","amazon.","ebay.","justice.gov","latofonts.com",
               "netcare.co.za","rppc.co.za","salamanderthemes.net","iafrica.co.za"]

def ok_email(e):
    e = e.lower().strip()
    if "@" not in e or len(e) < 6 or len(e) > 70: return False
    if any(b in e for b in BAD_LOCAL): return False
    if any(b in e.split("@")[1] for b in BAD_DOMAINS): return False
    if re.search(r'@\d+\.\d+', e): return False
    if any(c in e for c in ['&','"',"'",'<','>',';']): return False
    if e.endswith((".png",".jpg",".gif",".css",".js",".svg")): return False
    domain = e.split("@")[1]
    if "." not in domain or len(domain.split(".")[-1]) < 2: return False
    return True

MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "NPO-Outreach/1.0 (educational; mrnnsu001@myuct.ac.za)"}

def overpass_query(lat, lon, radius, tk, tv):
    q = f'[out:json][timeout:30];(node["{tk}"="{tv}"](around:{radius},{lat},{lon});way["{tk}"="{tv}"](around:{radius},{lat},{lon}););out body;'
    for url in MIRRORS:
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=45)
            if r.status_code == 200: return r.json().get("elements", [])
        except: continue
    return []

def is_healthcare(tags):
    return (tags.get("amenity") in ("hospital","clinic","doctors","dentist",
                                     "pharmacy","nursing_home","veterinary")
            or "healthcare" in tags or tags.get("social_facility") == "medical")

def in_suburb(tags, lat, lon, target):
    addr = " ".join([tags.get("addr:suburb",""), tags.get("addr:street",""), tags.get("addr:city","")]).lower()
    target_low = target.lower()
    for wrong in ["observatory","rosebank","claremont","salt river","woodstock","newlands","athlone"]:
        if wrong in addr: return False
    if target_low in addr: return True
    return True  # trust 900m radius

def emails_from_site(url, timeout=8):
    if not url or not url.startswith("http"): return []
    try:
        p = urlparse(url)
        if any(b in p.netloc.lower() for b in BAD_DOMAINS): return []
    except: return []
    base = f"{p.scheme}://{p.netloc}"
    found = set()
    for path in ["", "/contact", "/contact-us"]:
        try:
            r = requests.get(base+path, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200: continue
            html = r.text[:100000]
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
        print("Usage: scraper_overpass.py <suburb> <category>"); sys.exit(1)
    suburb, category = sys.argv[1], sys.argv[2]
    if suburb not in LOCATIONS: print(f"❌ Use: {list(LOCATIONS.keys())}"); sys.exit(1)
    if category not in CATEGORY_TAGS: print(f"❌ Unknown. Available: {list(CATEGORY_TAGS.keys())}"); sys.exit(1)

    lat, lon, radius = LOCATIONS[suburb]
    queries = CATEGORY_TAGS[category]
    print(f"🔍 {suburb} — {category} (radius {radius}m, {len(queries)} tags)")

    all_places = {}
    for tk, tv in queries:
        for p in overpass_query(lat, lon, radius, tk, tv):
            tags = p.get("tags", {})
            name = tags.get("name","").strip()
            if not name or is_healthcare(tags): continue
            if not in_suburb(tags, p.get("lat",lat), p.get("lon",lon), suburb): continue
            pid = p.get("id")
            if pid not in all_places:
                all_places[pid] = {
                    "name": name,
                    "website": tags.get("website","") or tags.get("contact:website",""),
                    "email": tags.get("email","") or tags.get("contact:email",""),
                    "phone": tags.get("phone","") or tags.get("contact:phone",""),
                }
        time.sleep(0.4)

    print(f"  → {len(all_places)} in-area non-health places")
    rows = []
    for pid, p in all_places.items():
        emails = []
        if p["email"] and ok_email(p["email"]):
            emails.append(p["email"].lower())
        if not emails and p["website"]:
            emails = emails_from_site(p["website"])
        if not emails:
            print(f"  – {p['name']}"); continue
        for e in emails:
            rows.append({"Organisation Name": p["name"], "Category": category, "Location": suburb,
                         "Email": e, "Phone": p["phone"], "Website": p["website"]})
        print(f"  ✅ {p['name']} → {emails[0]}")

    if not rows: print("  no emails"); sys.exit(0)
    df = pd.DataFrame(rows).drop_duplicates("Email").drop_duplicates(subset=["Organisation Name"], keep="first")
    os.makedirs("results", exist_ok=True)
    out = f"results/scraped_{suburb}_{category.replace(' ','_').replace('&','and')}.xlsx"
    df.to_excel(out, index=False)
    print(f"✅ {len(df)} saved → {out}")

if __name__ == "__main__":
    main()
