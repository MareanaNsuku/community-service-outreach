#!/bin/bash
set -e
cd /workspaces/community-service-outreach
set -a; source .env.local; set +a

echo "=== 1. Filter to Mowbray/Rondebosch ==="
python3 << 'PYEOF'
import sys, pandas as pd
df = pd.read_csv("new_contacts.csv")
print(f"Loaded {len(df)} rows from new_contacts.csv")
loc = "Suburb" if "Suburb" in df.columns else "Location"
df["Location"] = df[loc].astype(str).str.strip()
df["LocLow"] = df["Location"].str.lower()
ALLOWED = {"mowbray", "rondebosch"}
keep = df[df["LocLow"].isin(ALLOWED)].copy()
drop = df[~df["LocLow"].isin(ALLOWED)]
if len(drop):
    print(f"⛔ Dropped {len(drop)} outside Mowbray/Rondebosch")
if keep.empty:
    print("❌ No Mowbray/Rondebosch rows"); sys.exit(1)
keep["Email"] = keep["Email"].astype(str).str.lower().str.strip()
keep = keep[keep["Email"].str.contains("@", na=False)].drop_duplicates("Email")
keep["Category"] = "Community Development"
keep["Sent"] = ""
keep[["Organisation Name","Category","Location","Email","Sent"]].to_excel("/tmp/mr_new.xlsx", index=False)
print(f"✅ Prepared {len(keep)} contacts")
PYEOF

echo ""
echo "=== 2. Backup + append to master ==="
python3 << 'PYEOF'
import sys, pandas as pd
from datetime import datetime
new = pd.read_excel("/tmp/mr_new.xlsx")
master = pd.read_excel("results/master_contacts.xlsx")
bl = set(pd.read_excel("results/blocklist.xlsx")["Email"].astype(str).str.lower().str.strip())
master["Email"] = master["Email"].fillna("").astype(str).str.lower().str.strip()
new["Email"] = new["Email"].fillna("").astype(str).str.lower().str.strip()
existing = set(master["Email"]) | bl
new = new[~new["Email"].isin(existing)].drop_duplicates("Email")
if new.empty:
    print("ℹ️  Nothing new after dedup"); open("/tmp/mr_status","w").write("empty"); sys.exit(0)
ts = datetime.now().strftime('%Y%m%d-%H%M%S')
master.to_excel(f"results/master_contacts.backup-{ts}.xlsx", index=False)
print(f"💾 Backup saved")
for col in master.columns:
    if col not in new.columns: new[col] = ""
new = new[master.columns]
combined = pd.concat([master, new], ignore_index=True)
combined.to_excel("results/master_contacts.xlsx", index=False)
print(f"✅ Appended {len(new)}. Master: {len(combined)} rows")
for _, r in new.iterrows():
    print(f"   + {r['Organisation Name']} — {r['Email']}")
open("/tmp/mr_emails.txt","w").write("\n".join(new["Email"].tolist()))
open("/tmp/mr_status","w").write("ok")
PYEOF

if [ "$(cat /tmp/mr_status)" != "ok" ]; then echo "Nothing to send. Done."; exit 0; fi

echo ""
echo "=== 3. Send ONLY the new contacts ==="
python3 << 'PYEOF'
import pandas as pd
from send_emails import send_emails
emails = [e.strip() for e in open("/tmp/mr_emails.txt") if e.strip()]
m = pd.read_excel("results/master_contacts.xlsx")
m["Email"] = m["Email"].fillna("").astype(str).str.lower().str.strip()
batch = m[m["Email"].isin(emails) & (m["Sent"].astype(str).str.lower() != "yes")].copy()
print(f"Sending to {len(batch)} contacts")
batch.to_excel("/tmp/mr_send.xlsx", index=False)
send_emails("/tmp/mr_send.xlsx")
PYEOF

echo ""
echo "=== 4. Mark as Sent ==="
python3 << 'PYEOF'
import pandas as pd
emails = [e.strip() for e in open("/tmp/mr_emails.txt") if e.strip()]
m = pd.read_excel("results/master_contacts.xlsx")
m["Email"] = m["Email"].fillna("").astype(str).str.lower().str.strip()
mask = m["Email"].isin(emails)
m.loc[mask, "Sent"] = "Yes"
m.to_excel("results/master_contacts.xlsx", index=False)
print(f"✅ Marked {mask.sum()} as Sent")
PYEOF

echo ""
echo "=== 5. Commit + push ==="
git add results/master_contacts.xlsx new_contacts.csv
git commit -m "Add + send Mowbray/Rondebosch $(date +%Y%m%d-%H%M)" || echo "no change"
git push origin main

echo ""
echo "=== SUMMARY ==="
python3 -c "
import pandas as pd
m = pd.read_excel('results/master_contacts.xlsx')
sent = (m['Sent'].astype(str).str.lower()=='yes').sum()
mr = m[m['Location'].astype(str).str.lower().isin(['mowbray','rondebosch'])]
mr_sent = (mr['Sent'].astype(str).str.lower()=='yes').sum()
print(f'Master: {len(m)} | Total sent: {sent}')
print(f'Mowbray/Rondebosch: {len(mr)} | Sent: {mr_sent}')
"
