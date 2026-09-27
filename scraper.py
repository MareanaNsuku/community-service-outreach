import os, re, sys, time, random
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

CATEGORY_TERMS = {
    "Sports & Recreation": [
        "sports club", "recreation centre", "youth sports", "athletics club",
        "football club", "rugby club", "cricket club", "swimming club",
        "tennis club", "netball club", "sports development",
    ],
    "Animal Welfare": [
        "animal shelter", "SPCA", "animal rescue", "wildlife rehabilitation",
        "pet rescue", "animal welfare", "animal anti-cruelty",
        "dog rescue", "cat rescue", "bird sanctuary",
    ],
    "Environmental": [
        "environmental organisation", "conservation trust", "recycling initiative",
        "community garden", "clean-up crew", "wetland guardians",
        "tree planting", "climate action", "eco warriors", "sustainability",
    ],
    "Arts & Culture": [
        "art centre", "community theatre", "dance company", "music academy",
        "art gallery", "cultural centre", "photographic society", "choir",
        "youth orchestra", "craft market", "poetry slam",
    ],
    "Youth & Tutoring": [
        "youth centre", "tutoring centre", "after-school programme",
        "literacy project", "homework club", "youth development",
        "leadership academy", "mentorship programme", "reading project",
        "educational support",
    ],
}

def scrape_infoisinfo(city, term):
    results = []
    slug = city.lower().replace(" ", "-")
    url = f"https://{slug}.infoisinfo.co.za/search/{quote_plus(term.replace(' ', '-'))}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".result, .listing, .company"):
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
    except Exception as e:
        print(f"  [Infoisinfo] {e}")
    return results

def scrape_yellowpages(city, term):
    results = []
    try:
        url = f"https://www.yellowpages.co.za/search?what={quote_plus(term)}&where={quote_plus(city)}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".listing, .result, .search-result"):
            name_el = card.select_one("h2, h3, .name, a.title")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            phone_el = card.select_one(".phone, .tel")
            phone = phone_el.get_text(strip=True) if phone_el else ""
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": phone, "Website": "", "Address": "",
                "Source": "YellowPages",
            })
    except Exception as e:
        print(f"  [YellowPages] {e}")
    return results

def scrape_ngopulse(city, term):
    results = []
    try:
        url = f"https://www.ngopulse.org/directory?search={quote_plus(term)}&province=Western%20Cape"
        r = requests.get(url, headers=HEADERS, timeout=15)
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
    except Exception as e:
        print(f"  [NGO Pulse] {e}")
    return results

def scrape_forgood(city, term):
    results = []
    try:
        url = f"https://www.forgood.co.za/volunteer/opportunities?location={quote_plus(city)}"
        r = requests.get(url, headers=HEADERS, timeout=15)
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
    except Exception as e:
        print(f"  [ForGood] {e}")
    return results

def scrape_brabys(city, term):
    results = []
    try:
        url = f"https://www.brabys.com/search?q={quote_plus(term)}&location={quote_plus(city)}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".listing, .result, .brabys-listing"):
            name_el = card.select_one("h2, h3, .name, a")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue
            phone_el = card.select_one(".phone, .tel")
            phone = phone_el.get_text(strip=True) if phone_el else ""
            results.append({
                "Organisation Name": name, "Category": None, "Location": city,
                "Email": "", "Phone": phone, "Website": "", "Address": "",
                "Source": "Brabys",
            })
    except Exception as e:
        print(f"  [Brabys] {e}")
    return results

def fetch_email_from_site(url):
    if not url or not url.startswith("http"):
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        emails = EMAIL_REGEX.findall(r.text)
        emails = [e for e in emails if not any(
            bad in e.lower() for bad in ["example.com", "sentry", "wixpress", ".png", ".jpg"]
        )]
        if emails:
            return emails[0]
        for slug in ["/contact", "/contact-us", "/about", "/about-us"]:
            try:
                r2 = requests.get(urljoin(url, slug), headers=HEADERS, timeout=8)
                emails2 = EMAIL_REGEX.findall(r2.text)
                emails2 = [e for e in emails2 if not any(
                    bad in e.lower() for bad in ["example.com", "sentry", "wixpress"]
                )]
                if emails2:
                    return emails2[0]
            except Exception:
                continue
    except Exception:
        pass
    return ""

def scrape_all(city, category):
    terms = CATEGORY_TERMS.get(category, [category])
    all_results = []

    for term in terms:
        print(f"  -> Searching: '{term}' in {city}")
        all_results += scrape_infoisinfo(city, term)
        all_results += scrape_ngopulse(city, term)
        all_results += scrape_forgood(city, term)
        all_results += scrape_yellowpages(city, term)
        all_results += scrape_brabys(city, term)
        time.sleep(random.uniform(1.0, 2.5))

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

    print(f"  -> Enriching {len(unique)} results with website emails...")
    for i, r in enumerate(unique):
        if not r["Email"] and r["Website"]:
            email = fetch_email_from_site(r["Website"])
            if email:
                r["Email"] = email
                print(f"    [{i+1}/{len(unique)}] {r['Organisation Name']} -> {email}")
        time.sleep(0.3)

    return unique

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scraper.py <city> <category>")
        sys.exit(1)
    city = sys.argv[1]
    category = sys.argv[2]
    print(f"Scraping {category} organisations in {city}...")
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
    print(f"Saved {len(df)} organisations to {out}")
