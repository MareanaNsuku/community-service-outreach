#!/bin/bash
# Usage: bash run.sh
# Reads credentials from .env.local (not committed)

cd "$(dirname "$0")"

if [ -f ".env.local" ]; then
    set -a
    source .env.local
    set +a
else
    echo "❌ .env.local not found. Create it with:"
    echo "   BREVO_SMTP_LOGIN=..."
    echo "   BREVO_SMTP_PASSWORD=..."
    echo "   SENDER_EMAIL=..."
    exit 1
fi

FILE=$(ls inbox/*.xlsx inbox/*.xls 2>/dev/null | head -1)

if [ -z "$FILE" ]; then
    echo "ℹ️  inbox/ is empty — nothing to import"
    echo ""
    python3 -c "
import pandas as pd
df = pd.read_excel('results/master_contacts.xlsx')
sent = (df['Sent'].astype(str).str.lower() == 'yes').sum()
rem = df[(df['Sent'].astype(str).str.lower() != 'yes') & (df['Email'].notna()) & (df['Email'].astype(str).str.contains('@'))]
print(f'  Master: {len(df)} contacts')
print(f'  Sent: {sent} / {len(df)}')
print(f'  Remaining (with email): {len(rem)}')
print()
print('✅ System idle. Upload an Excel file to inbox/ to send.')
"
    exit 0
fi

echo "📂 Found: $FILE"
echo ""
echo "=== INGESTING ==="
python3 ingest_excel.py "$FILE" || { echo "❌ Ingest failed"; exit 1; }

echo ""
echo "=== SENDING ==="
bash send_subset.sh "Cape Town" "Imported"

echo ""
echo "=== SYNCING ==="
python3 sync_batch_to_master.py

echo ""
echo "=== PUSHING ==="
git add results/*.xlsx inbox/
git commit -m "New batch $(date -u +%Y-%m-%d-%H%M)" 2>/dev/null || echo "No changes"
git push origin main 2>/dev/null || echo "Nothing to push"

echo ""
echo "=== FINAL STATE ==="
python3 -c "
import pandas as pd
df = pd.read_excel('results/master_contacts.xlsx')
sent = (df['Sent'].astype(str).str.lower() == 'yes').sum()
rem = df[(df['Sent'].astype(str).str.lower() != 'yes') & (df['Email'].notna()) & (df['Email'].astype(str).str.contains('@'))]
print(f'  Master: {len(df)} contacts')
print(f'  Sent: {sent} / {len(df)} ({100*sent/len(df):.1f}%)')
print(f'  Remaining: {len(rem)}')
print()
print('✅ Done')
"
