#!/usr/bin/env python3
"""Check SerpApi quota without consuming searches."""
import os, json, time, requests
from datetime import datetime

CACHE_FILE = "/tmp/serpapi_quota.json"
CACHE_TTL = 300  # 5 min

def get_quota(force=False):
    key = os.getenv("SERPAPI_KEY", "")
    if not key:
        return {"ok": False, "remaining": 0, "error": "no_key", "used": 0, "total": 0}
    
    if not force and os.path.exists(CACHE_FILE):
        try:
            cached = json.load(open(CACHE_FILE))
            if time.time() - cached.get("ts", 0) < CACHE_TTL:
                return cached["data"]
        except: pass
    
    try:
        r = requests.get("https://serpapi.com/account",
                         params={"api_key": key}, timeout=10)
        if r.status_code != 200:
            data = {"ok": False, "remaining": 0, "error": f"http_{r.status_code}", "used": 0, "total": 0}
        else:
            j = r.json()
            data = {
                "ok": True,
                "remaining": j.get("plan_searches_left", 0),
                "used": j.get("this_month_usage", 0),
                "total": j.get("searches_per_month", 0),
                "plan": j.get("plan_name", "?"),
                "renewal": j.get("plan_renewal_date", "?"),
            }
    except Exception as e:
        data = {"ok": False, "remaining": 0, "error": str(e), "used": 0, "total": 0}
    
    try:
        json.dump({"ts": time.time(), "data": data}, open(CACHE_FILE, "w"))
    except: pass
    return data

if __name__ == "__main__":
    q = get_quota(force=True)
    if q["ok"]:
        print(f"SerpApi: {q['remaining']}/{q['total']} searches left ({q['used']} used)")
        print(f"Plan: {q['plan']} | Renews: {q['renewal']}")
        if q["remaining"] <= 0:
            print("⚠️  EXHAUSTED — hybrid will fall back to Overpass")
    else:
        print(f"SerpApi check failed: {q.get('error')}")
