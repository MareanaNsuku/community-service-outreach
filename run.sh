#!/bin/bash
# Safe send — refuses to send duplicates
cd "$(dirname "$0")"
set -a; source .env.local 2>/dev/null; set +a

FILE=$(ls inbox/*.xlsx inbox/*.xls 2>/dev/null | head -1)

if [ -z "$FILE" ]; then
    echo "ℹ️  inbox/ is empty"
    exit 0
fi

# Ingest
python3 ingest_excel.py "$FILE" 2>/dev/null || true

# Build pending list from master (only unsent)
python3 << 'PYEOF'
import pandas as pd
df = pd.read_excel('results/master_contacts.xlsx')
rem = df[(df['Sent'].astype(str).str.lower() != 'yes') & 
         (df['Email'].notna()) & 
         (df['Email'].astype(str).str.contains('@'))].copy()
rem['Sent'] = ''
for c in ['Organisation Name', 'Category', 'Location', 'Email', 'Phone', 'Website', 'Sent']:
    if c not in rem.columns:
        rem[c] = ''
rem[['Organisation Name', 'Category', 'Location', 'Email', 'Phone', 'Website', 'Sent']].to_excel('/tmp/pending.xlsx', index=False)
print(f"📋 {len(rem)} unsent contacts")
PYEOF

if [ ! -f /tmp/pending.xlsx ]; then
    echo "Nothing to send"
    exit 0
fi

# SAFETY GUARD — verify no duplicates
python3 safe_send.py /tmp/pending.xlsx || exit 1

# Send
python3 send_emails.py /tmp/pending.xlsx

# Mark as sent
python3 << 'PYEOF'
import pandas as pd
batch = pd.read_excel('/tmp/pending.xlsx')
master = pd.read_excel('results/master_contacts.xlsx')
for _, row in batch.iterrows():
    if str(row.get('Sent', '')).lower() == 'yes':
        mask = master['Email'].astype(str).str.lower() == str(row['Email']).lower()
        master.loc[mask, 'Sent'] = 'Yes'
master.to_excel('results/master_contacts.xlsx', index=False)
sent = (master['Sent'].astype(str).str.lower() == 'yes').sum()
print(f"✅ Total sent: {sent} / {len(master)}")
PYEOF

# Commit + push
git add results/*.xlsx inbox/
git commit -m "Auto-send $(date -u +%Y-%m-%d-%H%M)" 2>/dev/null || echo "No changes"
git push origin main 2>/dev/null || echo "Nothing to push"

rm -f /tmp/pending.xlsx
