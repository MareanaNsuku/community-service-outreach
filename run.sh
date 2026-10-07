#!/bin/bash
cd "$(dirname "$0")"
set -a; source .env.local 2>/dev/null; set +a

FILE=$(ls inbox/*.xlsx inbox/*.xls 2>/dev/null | head -1)

if [ -z "$FILE" ]; then
    echo "ℹ️  inbox/ is empty"
    exit 0
fi

# Ingest if it has contacts
python3 ingest_excel.py "$FILE" 2>/dev/null || true

# Build a pending batch of ALL unsent contacts
python3 << 'PYEOF'
import pandas as pd
df = pd.read_excel('results/master_contacts.xlsx')
rem = df[(df['Sent'].astype(str).str.lower() != 'yes') & (df['Email'].notna()) & (df['Email'].astype(str).str.contains('@'))].copy()
rem['Sent'] = ''
rem[['Organisation Name', 'Category', 'Location', 'Email', 'Phone', 'Website', 'Sent']].to_excel('/tmp/pending.xlsx', index=False)
print(f"📋 {len(rem)} unsent contacts")
PYEOF

# Send
python3 send_emails.py /tmp/pending.xlsx

# Sync + push
python3 sync_batch_to_master.py
git add results/*.xlsx inbox/
git commit -m "Auto-send $(date -u +%Y-%m-%d-%H%M)" 2>/dev/null || echo "No changes"
git push origin main 2>/dev/null || echo "Nothing to push"

rm -f /tmp/pending.xlsx
