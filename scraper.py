import os, re, sys, time, random, json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-ZA,en;q=0.9",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Only skip emails with these characteristics (not domains)
BAD_EMAIL_PATTERNS = [
    "example.com", "sentry", "wixpress", "domain.com", "test.com",
    "yourdomain", ".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg",
    "wordpress@", "info@wix.com", "noreply@", "no-reply@", "donotreply@",
    "postmaster@", "abuse@", "webmaster@localhost"
]

# Domains we DON'T want to visit for email enrichment (they don't have org emails)
# BUT we can still extract "real website" links from them
DIRECTORY_DOMAINS = [
    "infoisinfo", "yellosa", "forgood", "ngopulse", "cylex", "hotfrog",
    "brabys", "yellowpages", "saYellow", "businesslist", "showme"
]

# Social/irrelevant sites we never enrich from
SKIP_ENRICHMENT_DOMAINS = [
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com"
]

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
    "Community Development": ["community centre", "civic organisation",
        "community forum", "residents association", "community development",
        "community upliftment", "civic association", "community outreach",
        "community trust", "community project", "community improvement"],
    "Museums & Heritage": ["museum", "heritage site", "heritage centre", "cultural museum",
        "history museum", "art museum", "heritage trust", "heritage society",
        "local history", "heritage foundation", "museum volunteers"],
    "Libraries & Reading Programmes": ["public library", "community library", "reading club",
        "book club", "literacy programme", "reading programme", "library volunteers",
        "mobile library", "story time", "reading project"],
    "Public Parks & Gardens": ["botanical garden", "public park", "community garden",
        "rose garden", "nature garden", "park volunteers", "garden volunteers",
        "green spaces", "urban garden", "park friends"],
    "Cultural Centres & Community Halls": ["cultural centre", "community hall",
        "community centre", "civic centre", "multipurpose centre", "community hub",
        "neighbourhood centre", "arts centre", "cultural hub"],
    "Historic Sites & Preservation": ["historic site", "historical society",
        "heritage preservation", "historic building", "monument trust",
        "historical association", "preservation trust", "archive"],
    "Neighbourhood Associations": ["neighbourhood association", "residents association",
        "ratepayers association", "community forum", "neighbourhood watch",
        "civic association", "community committee", "ward committee"],
    "Community Media & Radio": ["community radio", "community newspaper", "local radio",
        "community media", "neighbourhood newsletter", "community blog",
        "community journalist", "local news", "community magazine"],
    "Community Markets & Farmers Markets": ["farmers market", "craft market",
        "community market", "weekend market", "local market", "market association",
        "vendor market", "street market"],
    "Performing Arts & Music Groups": ["choir", "band", "orchestra", "drama group",
        "theatre group", "dance group", "music group", "performing arts",
        "community theatre", "marching band", "a cappella"],
    "Adult Education & Skills Training": ["adult education", "skills training",
        "vocational training", "adult learning", "skills centre", "career training",
        "technical training", "adult literacy", "lifelong learning"],
    "Volunteer Centres & NGO Support": ["volunteer centre", "volunteer organisation",
        "volunteer bureau", "NGO support", "non-profit support", "civil society",
        "volunteer network", "volunteer coordination", "NGO hub"],
    "Tourism & Visitor Information": ["visitor centre", "tourism bureau", "tourist information",
        "visitor information", "tourism association", "tourism office",
        "tourism board", "visitor guide", "tourist centre"],
    "Community Events & Festivals": ["community festival", "street festival",
        "cultural festival", "community event", "heritage festival", "art festival",
        "food festival", "community celebration", "event committee"],
    "Hobby & Special Interest Clubs": ["photography club", "chess club", "hiking club",
        "astronomy club", "gardening club", "bird watching club", "model club",
        "board game club", "special interest group", "hobby group"],
}

CITY_SUBURBS = {
    "Cape Town": ["Cape Town CBD", "Sea Point", "Green Point", "Woodstock",
        "Observatory", "Salt River", "Mowbray", "Rondebosch", "Claremont", "Wynberg"],
    "Johannesburg": ["Johannesburg CBD", "Sandton", "Randbank", "Rosebank",
        "Soweto", "Midrand", "Roodepoort", "Alexandra", "Braamfontein", "Maboneng"],
}

def is_bad_email(email):
    el = email.lower()
    if len(el) < 6 or len(el) > 80:
        return True
    if el.count("@") != 1:
        return True
    local = el.split("@")[0]
    if len(local) < 2:
        return True
    return any(bad in el for bad in BAD_EMAIL_PATTERNS)

def extract_emails_from_html(html):
    """Extract and clean emails from HTML."""
    emails = EMAIL_REGEX.findall(html)
    return [e.lower() for e in emails if not is_bad_email(e)]

def pick_best_email(emails):
    """Prefer info@, contact@, admin@, etc."""
    if not emails:
        return ""
    # Deduplicate and sort by preference
    unique = list(set(emails))
    for pref in ["info@", "contact@", "admin@", "office@", "hello@", "enquiries@", "enquiry@", "reception@"]:
        for e in unique:
            if e.startswith(pref):
                return e
    return unique[0]

def fetch_email_from_site(url, timeout=6):
    """Visit an org's website and extract an email."""
    if not url or not url.startswith("http"):
        return ""
    # Skip social media and known dead-ends
    if any(d in url.lower() for d in SKIP_ENRICHMENT_DOMAINS):
        return ""
    # Skip directory domains themselves (their emails are not org emails)
    if any(d in url.lower() for d in DIRECTORY_DOMAINS):
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return ""
        emails = extract_emails_from_html(r.text)
        if emails:
            return pick_best_email(emails)
        # Try common contact pages
        for slug in ["/contact", "/contact-us", "/contactus", "/about",
                     "/about-us", "/get-in-touch", "/reach-us", "/team", "/kontak"]:
            try:
                r2 = requests.get(urljoin(url, slug), headers=HEADERS, timeout=4)
                if r2.status_code == 200:
                    emails2 = extract_emails_from_html(r2.text)
                    if emails2:
                        return pick_best_email(emails2)
            except Exception:
                continue
    except Exception:
        pass
    return ""

def extract_real_website_from_directory(dir_url):
    """If we land on a directory page, try to find the actual org's website link."""
    if not dir_url or not dir_url.startswith("http"):
        return ""
    try:
        r = requests.get(dir_url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(r.text, "html.parser")
        # Look for external links (the "visit website" button on directories)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if any(d in href.lower() for d in DIRECTORY_DOMAINS):
                continue
            if any(d in href.lower() for d in SKIP_ENRICHMENT_DOMAINS):
                continue
            if "google.com" in href.lower():
                continue
            text = a.get_text(strip=True).lower()
            if "website" in text or "visit" in text or "www" in href:
                return href
    except Exception:
        pass
    return ""

# ---------- Search engines ----------
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
            snippet_el = li.select_one(".b_caption p")
            snippet = snippet_el.get_text() if snippet_el else ""
            emails = extract_emails_from_html(snippet)
            email = pick_best_email(emails)
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
            emails = extract_emails_from_html(snippet)
            email = pick_best_email(emails)
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
            emails = extract_emails_from_html(snippet)
            email = pick_best_email(emails)
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
            emails = extract_emails_from_html(snippet)
            email = pick_best_email(emails)
            if not name or len(name) < 3:
                continue
            results.append({"Organisation Name": name[:120], "Category": None,
                "Location": city, "Email": email, "Phone": "", "Website": href,
                "Address": suburb or city, "Source": "Startpage"})
    except Exception:
        pass
    return results

# ---------- Main ----------
def scrape_all(city, category):
    terms = CATEGORY_TERMS.get(category, [category])[:10]
    suburbs = CITY_SUBURBS.get(city, [None])[:6]
    
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
            time.sleep(random.uniform(0.3, 0.8))
    
    # Deduplicate by name
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
    print(f"  -> Enriching emails (with directory→real-website resolution)...")
    
    enriched_count = 0
    for i, r in enumerate(unique):
        if r["Email"]:
            enriched_count += 1
            continue
        
        website = r["Website"]
        if not website:
            continue
        
        # If it's a directory page, extract the REAL org website first
        is_directory = any(d in website.lower() for d in DIRECTORY_DOMAINS)
        if is_directory:
            real_site = extract_real_website_from_directory(website)
            if real_site:
                r["Website"] = real_site
                email = fetch_email_from_site(real_site)
                if email:
                    r["Email"] = email
                    enriched_count += 1
        
        # Direct website enrichment
        if not r["Email"]:
            email = fetch_email_from_site(website)
            if email:
                r["Email"] = email
                enriched_count += 1
        
        if (i + 1) % 20 == 0:
            print(f"    [{i+1}/{len(unique)}] enriched: {enriched_count}")
        time.sleep(0.15)
    
    print(f"  -> Enriched {enriched_count} emails total")
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
    with_email = (df["Email"] != "").sum()
    print(f"✅ Saved {len(df)} orgs to {out} ({with_email} with emails)")
