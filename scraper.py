import os, re, sys, time, random, json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import pandas as pd

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-ZA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# ============================================================
# Expanded category search terms (20+ each)
# ============================================================
CATEGORY_TERMS = {
    "Sports & Recreation": [
        "sports club", "recreation centre", "youth sports", "athletics club",
        "football club", "soccer club", "rugby club", "cricket club",
        "swimming club", "tennis club", "netball club", "hockey club",
        "basketball club", "cycling club", "running club", "gymnastics",
        "martial arts", "surfing club", "rowing club", "sports development",
        "community sports", "sports academy", "youth football",
    ],
    "Animal Welfare": [
        "animal shelter", "SPCA", "animal rescue", "wildlife rehabilitation",
        "pet rescue", "animal welfare", "animal anti-cruelty",
        "dog rescue", "cat rescue", "bird sanctuary", "wildlife sanctuary",
        "animal hospital", "animal clinic", "animal protection",
        "marine animal rescue", "primate rescue", "horse rescue",
        "farm animal sanctuary", "animal foster", "animal adoption",
        "conservation animal", "wildlife trust",
    ],
    "Environmental": [
        "environmental organisation", "conservation trust", "recycling initiative",
        "community garden", "clean-up crew", "wetland guardians",
        "tree planting", "climate action", "eco warriors", "sustainability",
        "environmental education", "green initiative", "beach cleanup",
        "river cleanup", "urban farming", "permaculture", "food garden",
        "reforestation", "wildlife conservation", "nature reserve",
        "eco club", "environmental justice", "zero waste",
    ],
    "Arts & Culture": [
        "art centre", "community theatre", "dance company", "music academy",
        "art gallery", "cultural centre", "photographic society", "choir",
        "youth orchestra", "craft market", "poetry slam", "art studio",
        "theatre company", "drama society", "music school", "ballet school",
        "art project", "community art", "mural project", "film society",
        "writers guild", "cultural trust", "heritage organisation",
    ],
    "Youth & Tutoring": [
        "youth centre", "tutoring centre", "after-school programme",
        "literacy project", "homework club", "youth development",
        "leadership academy", "mentorship programme", "reading project",
        "educational support", "youth empowerment", "youth skills",
        "study support", "matric support", "career guidance",
        "youth outreach", "community learning", "youth programme",
        "peer tutoring", "after school care", "youth trust",
        "educational ngo", "school support",
    ],
}

# ============================================================
# Suburb breakdowns for major cities (maximises coverage)
# ============================================================
CITY_SUBURBS = {
    "Cape Town": [
        "Cape Town CBD", "Sea Point", "Green Point", "Woodstock", "Observatory",
        "Salt River", "Mowbray", "Rondebosch", "Claremont", "Wynberg",
        "Athlone", "Bellville", "Parow", "Goodwood", "Milnerton",
        "Table View", "Durbanville", "Khayelitsha", "Mitchells Plain",
        "Gugulethu", "Nyanga", "Langa", "Muizenberg", "Fish Hoek",
        "Hout Bay", "Retreat", "Grassy Park", "Lotus River", "Philippi",
    ],
    "Johannesburg": [
        "Johannesburg CBD", "Sandton", "Randburg", "Rosebank", "Soweto",
        "Midrand", "Roodepoort", "Alexandra", "Braamfontein", "Maboneng",
        "Fourways", "Bedfordview", "Kempton Park", "Edenvale",
    ],
    "Randburg": ["Ferndale", "Bryanston", "Olivedale", "Northgate", "Kensington", "Linden"],
}

# ============================================================
# Helper: fetch email from website
# ============================================================
def fetch_email_from_site(url):
    if not url or not url.startswith("http"):
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        emails = EMAIL_REGEX.findall(r.text)
        emails = [e for e in emails if not any(
            bad in e.lower() for bad in ["example.com", "sentry", "wixpress", ".png", ".jpg", ".gif", "domain.com"]
        )]
        if emails:
            return emails[0]
        # Try common contact pages
        for slug in ["/contact", "/contact-us", "/about", "/about-us", "/get-in-touch", "/reach-us", "/team"]:
            try:
                r2 = requests.get(urljoin(url, slug), headers=HEADERS, timeout=6)
                emails2 = EMAIL_REGEX.findall(r2.text)
                emails2 = [e for e in emails2 if not any(
                    bad in e.lower() for bad in ["example.com", "sentry", "wixpress", "domain.com"]
                )]
                if emails2:
                    return emails2[0]
            except Exception:
                continue
    except Exception:
        pass
    return ""

# ============================================================
# SOURCE 1: DuckDuckGo (primary – best coverage)
# ============================================================
def scrape_duckduckgo(city, term, suburb=None):
    results = []
    if not HAS_DDGS:
        return results
    query_loc = suburb if suburb else city
    queries = [
        f"{term} {query_loc} email contact",
        f"{term} {query_loc} site:org.za",
        f"{term} {query_loc} site:co.za email",
    ]
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    for r in ddgs.text(q, max_results=20):
                        title = r.get("title", "").strip()
                        body = r.get("body", "")
                        href = r.get("href", "")
                        if not title or len(title) < 3:
                            continue
                        # Extract email from snippet
                        emails = EMAIL_REGEX.findall(body)
                        email = emails[0] if emails else ""
                        results.append({
                            "Organisation Name": title[:120],
                            "Category": None,
                            "Location": city,
                            "Email": email,
                            "Phone": "",
                            "Website": href,
                            "Address": suburb or city,
                            "Source": "DuckDuckGo",
                        })
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception:
                    continue
    except Exception as e:
        print(f"  [DDG] {e}")
    return results

# ============================================================
# SOURCE 2: Bing Search
# ============================================================
def scrape_bing(city, term, suburb=None):
    results = []
    query_loc = suburb if suburb else city
    try:
        url = f"https://www.bing.com/search?q={quote_plus(term + ' ' + query_loc + ' email contact')}"
        r = requests.get(url, headers=HEADERS, timeout=12)
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
            email = emails[0] if emails else ""
            results.append({
                "Organisation Name": name[:120],
                "Category": None,
                "Location": city,
                "Email": email,
                "Phone": "",
                "Website": link,
                "Address": suburb or city,
                "Source": "Bing",
            })
    except Exception as e:
        print(f"  [Bing] {e}")
    return results

# ============================================================
# SOURCE 3: Infoisinfo
# ============================================================
def scrape_infoisinfo(city, term):
    results = []
    slug = city.lower().replace(" ", "-")
    url = f"https://{slug}.infoisinfo.co.za/search/{quote_plus(term.replace(' ', '-'))}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".result, .listing, .company, .search-result"):
            name_el = card.select_one("h2, h3, .name, a.title")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            link = name_el.get("href") if name_el and name_el.get("href") else ""
            if link and not link.startswith("http"):
                link = urljoin(url, link)
            phone_el = card.select_one(".phone, .tel, [class*='phone']")
            phone = phone_el.get_text(strip=True) if phone_el else ""
            addr_el = card.select_one(".address, .location")
            addr = addr_el.get_text(strip=True) if addr_el else ""
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": phone, "Website": link, "Address": addr,
                "Source": "Infoisinfo",
            })
    except Exception:
        pass
    return results

# ============================================================
# SOURCE 4: NGO Pulse
# ============================================================
def scrape_ngopulse(city, term):
    results = []
    try:
        url = f"https://www.ngopulse.org/directory?search={quote_plus(term)}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".views-row, .directory-item"):
            name_el = card.select_one(".title a, h2 a, a.title")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name:
                continue
            link = name_el.get("href") if name_el else ""
            if link and not link.startswith("http"):
                link = "https://www.ngopulse.org" + link
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": "", "Website": link, "Address": "",
                "Source": "NGO Pulse",
            })
    except Exception:
        pass
    return results

# ============================================================
# SOURCE 5: ForGood
# ============================================================
def scrape_forgood(city, term):
    results = []
    try:
        url = f"https://www.forgood.co.za/volunteer/opportunities?location={quote_plus(city)}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".opportunity-card, .listing-card, .org-card"):
            name_el = card.select_one("h3, h4, .org-name, a.title")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": "", "Website": "", "Address": "",
                "Source": "ForGood",
            })
    except Exception:
        pass
    return results

# ============================================================
# SOURCE 6: Cylex South Africa
# ============================================================
def scrape_cylex(city, term):
    results = []
    try:
        url = f"https://www.cylex.co.za/s?q={quote_plus(term)}&loc={quote_plus(city)}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".result-item, .listing, .company"):
            name_el = card.select_one("h2, h3, a.name")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            phone_el = card.select_one(".phone, .tel")
            phone = phone_el.get_text(strip=True) if phone_el else ""
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": phone, "Website": "", "Address": "",
                "Source": "Cylex",
            })
    except Exception:
        pass
    return results

# ============================================================
# SOURCE 7: Hotfrog SA
# ============================================================
def scrape_hotfrog(city, term):
    results = []
    try:
        url = f"https://www.hotfrog.co.za/search/{quote_plus(city)}/{quote_plus(term)}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".business-card, .listing, .result"):
            name_el = card.select_one("h3, h2, .name, a")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": "", "Website": "", "Address": "",
                "Source": "Hotfrog",
            })
    except Exception:
        pass
    return results

# ============================================================
# Main scraper – city × suburbs × terms
# ============================================================
def scrape_all(city, category):
    terms = CATEGORY_TERMS.get(category, [category])
    # Limit terms per suburb to keep runtime reasonable
    terms = terms[:15]
    suburbs = CITY_SUBURBS.get(city, [None])[:10]  # top 10 suburbs

    all_results = []
    total_searches = len(terms) * len(suburbs)
    counter = 0

    for suburb in suburbs:
        for term in terms:
            counter += 1
            loc_label = suburb if suburb else city
            print(f"  [{counter}/{total_searches}] '{term}' in {loc_label}")

            all_results += scrape_duckduckgo(city, term, suburb)
            all_results += scrape_bing(city, term, suburb)

            # Hit directory sources only once per term (not per suburb)
            if suburb is None or suburbs.index(suburb) == 0:
                all_results += scrape_infoisinfo(city, term)
                all_results += scrape_ngopulse(city, term)
                all_results += scrape_forgood(city, term)
                all_results += scrape_cylex(city, term)
                all_results += scrape_hotfrog(city, term)

            time.sleep(random.uniform(0.8, 1.8))

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

    # Enrich emails
    print(f"  -> Enriching emails from websites...")
    enriched_count = 0
    for i, r in enumerate(unique):
        if not r["Email"] and r["Website"]:
            email = fetch_email_from_site(r["Website"])
            if email:
                r["Email"] = email
                enriched_count += 1
        if (i + 1) % 10 == 0:
            print(f"    [{i+1}/{len(unique)}] enriched so far: {enriched_count}")
        time.sleep(0.2)

    print(f"  -> Enriched {enriched_count} emails from websites")
    return unique


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scraper.py <city> <category>")
        sys.exit(1)
    city = sys.argv[1]
    category = sys.argv[2]

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
