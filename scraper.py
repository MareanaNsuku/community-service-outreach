import os, re, sys, time, random, json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-ZA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
BAD_EMAIL_PARTS = ["example.com", "sentry", "wixpress", "domain.com", "test.com", 
                   "yourdomain", "sentry.io", ".png", ".jpg", ".gif", ".css", ".js",
                   "support@wordpress", "info@wix", "noreply@", "no-reply@"]

# ============================================================
# EXPANDED CATEGORIES
# ============================================================
CATEGORY_TERMS = {
    "Sports & Recreation": ["sports club", "recreation centre", "youth sports", "athletics club",
        "football club", "soccer club", "rugby club", "cricket club", "swimming club",
        "tennis club", "netball club", "hockey club", "basketball club", "cycling club",
        "running club", "gymnastics", "martial arts", "sports development"],
    "Animal Welfare": ["animal shelter", "SPCA", "animal rescue", "wildlife rehabilitation",
        "pet rescue", "animal welfare", "animal anti-cruelty", "dog rescue", "cat rescue",
        "bird sanctuary", "wildlife sanctuary", "animal hospital", "animal clinic",
        "animal protection", "marine animal rescue", "horse rescue", "farm animal sanctuary"],
    "Environmental": ["environmental organisation", "conservation trust", "recycling initiative",
        "community garden", "clean-up crew", "wetland guardians", "tree planting",
        "climate action", "eco warriors", "sustainability", "environmental education",
        "green initiative", "beach cleanup", "river cleanup", "urban farming",
        "permaculture", "reforestation", "nature reserve", "zero waste"],
    "Arts & Culture": ["art centre", "community theatre", "dance company", "music academy",
        "art gallery", "cultural centre", "photographic society", "choir", "youth orchestra",
        "craft market", "poetry slam", "art studio", "theatre company", "drama society",
        "music school", "ballet school", "art project", "community art", "film society"],
    "Youth & Tutoring": ["youth centre", "tutoring centre", "after-school programme",
        "literacy project", "homework club", "youth development", "leadership academy",
        "mentorship programme", "reading project", "educational support", "youth empowerment",
        "youth skills", "study support", "matric support", "career guidance",
        "youth outreach", "community learning", "peer tutoring"],
    
    # ============================================================
    # NEW CATEGORIES
    # ============================================================
    "Health & Wellness": ["community clinic", "hospice", "mental health support",
        "health outreach", "primary health care", "wellness centre", "counselling service",
        "rehabilitation centre", "health NGO", "medical charity", "dental clinic",
        "HIV support", "TB clinic", "maternal health", "child health clinic",
        "palliative care", "trauma centre", "rape crisis centre"],
    
    "Senior Care": ["old age home", "retirement village", "senior centre",
        "elderly care", "frail care", "aged care association", "senior citizen club",
        "meals on wheels", "elderly support", "old age service", "senior outreach",
        "golden age club", "pensioner support"],
    
    "Community Development": ["community centre", "civic organisation",
        "neighbourhood watch", "community forum", "residents association",
        "community development", "community upliftment", "civic association",
        "community outreach", "community trust", "community project",
        "community improvement", "ward committee"],
    
    "Women & Family Support": ["women shelter", "women empowerment",
        "gender-based violence support", "family support", "single mother support",
        "women development", "women outreach", "family counselling",
        "abused women support", "women resource centre", "safe house",
        "family violence centre", "women's health"],
    
    "Emergency & Rescue": ["fire brigade volunteer", "emergency services",
        "sea rescue", "mountain rescue", "disaster relief", "first aid",
        "ambulance volunteer", "search and rescue", "emergency response",
        "civil defence", "disaster management", "crisis response"],
}

# Suburbs for major cities
CITY_SUBURBS = {
    "Cape Town": ["Cape Town CBD", "Sea Point", "Green Point", "Woodstock",
        "Observatory", "Salt River", "Mowbray", "Rondebosch", "Claremont", "Wynberg",
        "Athlone", "Bellville", "Parow", "Goodwood", "Milnerton", "Table View",
        "Durbanville", "Khayelitsha", "Mitchells Plain", "Gugulethu"],
    "Johannesburg": ["Johannesburg CBD", "Sandton", "Randburg", "Rosebank",
        "Soweto", "Midrand", "Roodepoort", "Alexandra", "Braamfontein", "Maboneng"],
}

def is_bad_email(email):
    el = email.lower()
    return any(bad in el for bad in BAD_EMAIL_PARTS)

def fetch_email_from_site(url, timeout=6):
    if not url or not url.startswith("http"):
        return ""
    # Skip known directories (their emails are not the org's)
    skip_domains = ["infoisinfo", "yellosa", "forgood", "ngopulse", "cylex", "hotfrog",
                    "brabys", "yellowpages", "facebook.com", "twitter.com",
                    "instagram.com", "linkedin.com", "youtube.com"]
    if any(d in url.lower() for d in skip_domains):
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return ""
        emails = EMAIL_REGEX.findall(r.text)
        emails = [e for e in emails if not is_bad_email(e)]
        if emails:
            # Prefer info@, contact@, admin@
            for pref in ["info@", "contact@", "admin@", "office@", "hello@"]:
                for e in emails:
                    if e.lower().startswith(pref):
                        return e
            return emails[0]
        # Try contact pages
        for slug in ["/contact", "/contact-us", "/about", "/about-us",
                     "/get-in-touch", "/reach-us", "/team", "/kontak"]:
            try:
                r2 = requests.get(urljoin(url, slug), headers=HEADERS, timeout=4)
                emails2 = EMAIL_REGEX.findall(r2.text)
                emails2 = [e for e in emails2 if not is_bad_email(e)]
                if emails2:
                    return emails2[0]
            except Exception:
                continue
    except Exception:
        pass
    return ""

# ------------------ Search engines ------------------
def scrape_bing(city, term, suburb=None):
    results = []
    query_loc = suburb if suburb else city
    try:
        url = f"https://www.bing.com/search?q={quote_plus(term + ' ' + query_loc + ' contact email')}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("li.b_algo"):
            h2 = li.select_one("h2 a")
            if not h2:
                continue
            name = h2.get_text(strip=True)
            link = h2.get("href", "")
            snippet = li.select_one(".b_caption p")
            snippet_text = snippet.get_text() if snippet else ""
            emails = EMAIL_REGEX.findall(snippet_text)
            email = emails[0] if emails and not is_bad_email(emails[0]) else ""
            if not name or len(name) < 3:
                continue
            results.append({"Organisation Name": name[:120], "Category": None,
                "Location": city, "Email": email, "Phone": "", "Website": link,
                "Address": suburb or city, "Source": "Bing"})
    except Exception:
        pass
    return results

def scrape_mojeek(city, term, suburb=None):
    results = []
    query_loc = suburb if suburb else city
    try:
        url = f"https://www.mojeek.com/search?q={quote_plus(term + ' ' + query_loc + ' contact')}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("li.result"):
            a = li.select_one("a.title, h2 a")
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a.get("href", "")
            snippet_el = li.select_one("p.s")
            snippet = snippet_el.get_text() if snippet_el else ""
            emails = EMAIL_REGEX.findall(snippet)
            email = emails[0] if emails and not is_bad_email(emails[0]) else ""
            if not name or len(name) < 3:
                continue
            results.append({"Organisation Name": name[:120], "Category": None,
                "Location": city, "Email": email, "Phone": "", "Website": href,
                "Address": suburb or city, "Source": "Mojeek"})
    except Exception:
        pass
    return results

def scrape_ecosia(city, term, suburb=None):
    results = []
    query_loc = suburb if suburb else city
    try:
        url = f"https://www.ecosia.org/search?q={quote_plus(term + ' ' + query_loc + ' contact')}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        for result in soup.select("article.result, .result-body"):
            a = result.select_one("a.result__link, h2 a")
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a.get("href", "")
            snippet_el = result.select_one(".result__description, p")
            snippet = snippet_el.get_text() if snippet_el else ""
            emails = EMAIL_REGEX.findall(snippet)
            email = emails[0] if emails and not is_bad_email(emails[0]) else ""
            if not name or len(name) < 3:
                continue
            results.append({"Organisation Name": name[:120], "Category": None,
                "Location": city, "Email": email, "Phone": "", "Website": href,
                "Address": suburb or city, "Source": "Ecosia"})
    except Exception:
        pass
    return results

def scrape_startpage(city, term, suburb=None):
    results = []
    query_loc = suburb if suburb else city
    try:
        url = f"https://www.startpage.com/sp/search?query={quote_plus(term + ' ' + query_loc + ' contact')}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        for result in soup.select(".w-gl__result, .result"):
            a = result.select_one("a.w-gl__result-title, h3 a")
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a.get("href", "")
            snippet_el = result.select_one(".w-gl__description, p")
            snippet = snippet_el.get_text() if snippet_el else ""
            emails = EMAIL_REGEX.findall(snippet)
            email = emails[0] if emails and not is_bad_email(emails[0]) else ""
            if not name or len(name) < 3:
                continue
            results.append({"Organisation Name": name[:120], "Category": None,
                "Location": city, "Email": email, "Phone": "", "Website": href,
                "Address": suburb or city, "Source": "Startpage"})
    except Exception:
        pass
    return results

# ------------------ Main orchestration ------------------
def scrape_all(city, category):
    terms = CATEGORY_TERMS.get(category, [category])[:15]
    suburbs = CITY_SUBURBS.get(city, [None])[:10]
    
    all_results = []
    total = len(terms) * len(suburbs)
    counter = 0
    
    for suburb in suburbs:
        for term in terms:
            counter += 1
            loc_label = suburb if suburb else city
            print(f"  [{counter}/{total}] '{term}' in {loc_label}")
            
            all_results += scrape_bing(city, term, suburb)
            all_results += scrape_mojeek(city, term, suburb)
            all_results += scrape_ecosia(city, term, suburb)
            all_results += scrape_startpage(city, term, suburb)
            time.sleep(random.uniform(0.4, 1.0))
    
    # Deduplicate
    seen = set()
    unique = []
    for r in all_results:
        key = r["Organisation Name"].strip().lower()
        if key in seen or len(key) < 3:
            continue
        seen.add(key)
        r["Category"] = category
        unique.append(r)
    
    print(f"  -> {len(unique)} unique organisations found")
    
    # Aggressive email enrichment
    print(f"  -> Enriching emails from websites...")
    enriched_count = 0
    for i, r in enumerate(unique):
        if not r["Email"] and r["Website"]:
            email = fetch_email_from_site(r["Website"])
            if email:
                r["Email"] = email
                enriched_count += 1
        # Show progress every 25
        if (i + 1) % 25 == 0:
            print(f"    [{i+1}/{len(unique)}] enriched: {enriched_count}")
        # Faster enrichment
        if not r["Email"]:
            time.sleep(0.1)
    
    print(f"  -> Enriched {enriched_count} emails from websites")
    return unique

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scraper.py <city> <category>")
        sys.exit(1)
    city, category = sys.argv[1], sys.argv[2]
    print(f"🔍 Intensive scrape: {category} in {city}")
    results = scrape_all(city, category)
    os.makedirs("results", exist_ok=True)
    safe_city = city.replace(" ", "_")
    safe_cat = category.replace(" ", "_").replace("&", "and")
    out = f"results/scraped_{safe_city}_{safe_cat}.xlsx"
    df = pd.DataFrame(results)
    cols = ["Organisation Name", "Category", "Location", "Email", "Phone", "Website", "Address", "Source"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    df.to_excel(out, index=False, engine="xlsxwriter")
    print(f"✅ Saved {len(df)} organisations to {out}")
