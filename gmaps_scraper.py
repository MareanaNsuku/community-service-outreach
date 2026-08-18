import sys, time, urllib.parse, os, re, json
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_via_json(page, max_results):
    """Try to extract results from embedded JSON. Returns list if successful, else None."""
    content = page.content()
    pattern = r'window\.APP_INITIALIZATION_STATE\s*=\s*(.+?);\s*window\.APP_FLAGS'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        match = re.search(r'window\.APP_INITIALIZATION_STATE\s*=\s*(.+?);', content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except:
        return None
    results_array = None
    for path in [[3,2,0,0,3], [3,1,0,3], [3,0,0,3], [3,2,0,3]]:
        try:
            arr = data
            for idx in path:
                arr = arr[idx]
            if isinstance(arr, list) and len(arr) > 0:
                results_array = arr
                break
        except:
            continue
    if not results_array:
        return None
    results = []
    for item in results_array:
        if len(results) >= max_results:
            break
        try:
            name = item[14][11] if len(item) > 14 and item[14] else None
            if not name or not isinstance(name, str) or name.startswith("Ad ·"):
                continue
            website = ""
            stack = [item]
            while stack:
                elem = stack.pop()
                if isinstance(elem, list):
                    stack.extend(elem)
                elif isinstance(elem, str) and elem.startswith("http"):
                    website = elem
                    break
            address = ""
            try:
                address = item[183][1][0] if len(item) > 183 and item[183] else ""
            except:
                pass
            phone = ""
            try:
                phone = item[178][0][0] if len(item) > 178 and item[178] else ""
            except:
                pass
            category = ""
            try:
                cat_val = item[13]
                if cat_val and isinstance(cat_val, list) and len(cat_val) > 0:
                    category = str(cat_val[0])
            except:
                pass
            results.append({
                "Organisation Name": name,
                "Address": address,
                "Phone": phone,
                "Website": website,
                "Category": category,
                "Source": "Google Maps"
            })
        except:
            continue
    return results if results else None

def scrape_via_clicks(page, max_results):
    """Click each result and extract details from side panel."""
    results = []
    cards = page.locator("a[aria-label]")
    count = cards.count()
    for i in range(min(count, max_results*2)):
        if len(results) >= max_results:
            break
        try:
            card = cards.nth(i)
            aria_label = card.get_attribute("aria-label")
            name = aria_label.split(",")[0].strip()
            if name.startswith("Ad ·") or name.startswith("Visit "):
                continue
            card.click()
            page.wait_for_selector("button[data-item-id*='address']", timeout=3000)
            page.wait_for_timeout(200)
            details = {"Organisation Name": name}
            addr = page.locator("button[data-item-id*='address']")
            details["Address"] = addr.first.inner_text() if addr.count() > 0 else ""
            phone_el = page.locator("button[data-item-id*='phone']")
            details["Phone"] = phone_el.first.inner_text() if phone_el.count() > 0 else ""
            site = page.locator("a[data-item-id*='authority']")
            details["Website"] = site.first.get_attribute("href") if site.count() > 0 else ""
            cat_el = page.locator("button[jsaction*='pane.rating.category']")
            details["Category"] = cat_el.first.inner_text() if cat_el.count() > 0 else ""
            details["Source"] = "Google Maps"
            results.append(details)
            close_btn = page.locator("button[aria-label='Close']")
            if close_btn.count() > 0:
                close_btn.first.click()
                page.wait_for_timeout(200)
        except:
            try:
                page.click("button[aria-label='Close']", timeout=1000)
            except:
                pass
            continue
    return results

def scrape_google_maps(query, max_results=20):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # Attempt 1: JSON extraction (fast)
        print("   Trying JSON extraction...")
        results = scrape_via_json(page, max_results)
        if results:
            print(f"   JSON success: {len(results)} results")
            browser.close()
            return results

        # Attempt 2: click method (reliable)
        print("   JSON failed – switching to click method...")
        results = scrape_via_clicks(page, max_results)
        browser.close()
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gmaps_scraper.py <location> [search_term]")
        sys.exit(1)
    location = sys.argv[1]
    search_term = sys.argv[2] if len(sys.argv) > 2 else "community centre"
    query = f"{search_term} in {location}"
    print(f"🔍 Searching Google Maps: {query}")
    data = scrape_google_maps(query, max_results=20)
    if not data:
        print("No results found.")
    else:
        safe = location.replace(' ', '_').replace(",", "").replace("'", "")
        filename = f"results/gmaps_{safe}.xlsx"
        os.makedirs("results", exist_ok=True)
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='xlsxwriter')
        print(f"✅ Saved {len(data)} results to {filename}")
