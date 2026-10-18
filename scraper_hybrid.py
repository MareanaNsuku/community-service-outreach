#!/usr/bin/env python3
"""Hybrid scraper: SerpApi if quota available, else Overpass fallback."""
import os, sys, subprocess
from serpapi_quota import get_quota

MIN_BUFFER = 5  # don't burn last 5 searches

def run(script, suburb, category):
    print(f"\n▶  python3 {script} {suburb} {category}")
    r = subprocess.run(["python3", script, suburb, category],
                       capture_output=True, text=True, timeout=600)
    print(r.stdout)
    if r.stderr.strip(): print(r.stderr, file=sys.stderr)
    return r.returncode

def main():
    if len(sys.argv) < 3:
        print("Usage: scraper_hybrid.py <suburb> <category>")
        sys.exit(1)
    suburb, category = sys.argv[1], sys.argv[2]
    
    q = get_quota()
    remaining = q.get("remaining", 0)
    used = q.get("used", 0)
    total = q.get("total", 0)
    
    print(f"📊 SerpApi quota: {remaining}/{total} remaining ({used} used)")
    
    if remaining > MIN_BUFFER:
        print(f"✅ Using SerpApi (Google Maps) — {remaining} searches left")
        rc = run("scraper_maps.py", suburb, category)
        # Fall back to Overpass if SerpApi returned 0 places
        # (e.g., quota still >0 but query failed silently)
        return
    else:
        print(f"⚠️  SerpApi exhausted (remaining={remaining} ≤ buffer={MIN_BUFFER})")
        print(f"🔄 Falling back to Overpass (free)")
    
    rc = run("scraper_overpass.py", suburb, category)
    sys.exit(rc)

if __name__ == "__main__":
    main()
