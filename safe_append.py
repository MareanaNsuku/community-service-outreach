#!/usr/bin/env python3
"""Safe append — NEVER overwrites master. Adds only new emails."""
import sys, os
from datetime import datetime
import pandas as pd


def normalize_email(e):
    """Fix common malformations: trailing dots, double dots, whitespace."""
    e = str(e).strip().lower()
    e = e.replace(" ", "")
    while e.endswith(".") or e.endswith(","):
        e = e[:-1]
    e = e.replace("..", ".")
    return e

MASTER = "results/master_contacts.xlsx"
BLOCKLIST = "results/blocklist.xlsx"

def load_blocklist():
    try:
        return set(pd.read_excel(BLOCKLIST)["Email"].astype(str).str.lower().str.strip())
    except: return set()

def safe_append(scraped_file):
    if not os.path.exists(scraped_file):
        print(f"❌ Not found: {scraped_file}")
        return False

    # 1. BACKUP master first (refuse if backup fails)
    backup = f"results/master_contacts.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
    try:
        pd.read_excel(MASTER).to_excel(backup, index=False)
        print(f"💾 Backup: {backup}")
    except Exception as e:
        print(f"❌ Could not back up master: {e}")
        return False

    # 2. Load
    master = pd.read_excel(MASTER)
    new = pd.read_excel(scraped_file)

    # 3. Normalise email column
    master["Email"] = master["Email"].fillna("").astype(str).apply(normalize_email)
    new["Email"] = new["Email"].fillna("").astype(str).apply(normalize_email)

    # 4. Filter
    existing = set(master["Email"]) | load_blocklist()
    new = new[new["Email"].str.contains("@", na=False)]
    new = new[~new["Email"].isin(existing)]
    new = new.drop_duplicates("Email")

    if new.empty:
        print("ℹ️  No new contacts after dedup")
        return False

    # 5. Align columns to master
    for col in master.columns:
        if col not in new.columns:
            new[col] = ""
    new = new[master.columns]

    # 6. Ensure new rows have Sent="" (unsent)
    new["Sent"] = ""
    if "FollowUpSent" in new.columns: new["FollowUpSent"] = ""
    if "Replied" in new.columns: new["Replied"] = ""

    # 7. Append
    combined = pd.concat([master, new], ignore_index=True)
    combined.to_excel(MASTER, index=False)

    print(f"✅ Appended {len(new)} new contacts")
    print(f"   Master now: {len(combined)} rows")
    print(f"   New emails added:")
    for e in new["Email"].head(20):
        print(f"     • {e}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 safe_append.py <scraped_file.xlsx>")
        sys.exit(1)
    ok = safe_append(sys.argv[1])
    sys.exit(0 if ok else 1)
