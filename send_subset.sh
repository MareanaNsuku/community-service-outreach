#!/bin/bash
LOCATION="$1"
CATEGORY="$2"

if [ -z "$LOCATION" ] || [ -z "$CATEGORY" ]; then
    echo "Usage: bash send_subset.sh <location> <category>"
    exit 1
fi

mkdir -p results
SAFE_LOCATION="${LOCATION// /_}"
SAFE_CATEGORY="${CATEGORY// /_}"
SAFE_CATEGORY_CLEAN="${SAFE_CATEGORY//&/and}"
SCRAPED="results/scraped_${SAFE_LOCATION}_${SAFE_CATEGORY_CLEAN}.xlsx"
MERGED="results/merged_${SAFE_LOCATION}_${SAFE_CATEGORY_CLEAN}.xlsx"
OUTPUT="results/auto_${SAFE_LOCATION}_${SAFE_CATEGORY_CLEAN}.xlsx"

echo "========================================="
echo "STEP 1: Scraping new contacts (3-min timeout)"
echo "========================================="
echo "⏭️  Skipping scraper (using cached + curated contacts only)"

if [ -f "$SCRAPED" ]; then
    echo ""
    echo "========================================="
    echo "STEP 2: Preparing scraped contacts"
    echo "========================================="
    python3 merge_scraped.py "$SCRAPED" "$MERGED" && echo "✅ Prepared" || echo "⚠️ Merge failed"
fi

echo ""
echo "========================================="
echo "STEP 3: Loading curated contacts from master"
echo "========================================="
python3 query_master.py "$LOCATION" "$CATEGORY" --output "$OUTPUT"

# Combine scraped contacts with curated ones (dedupe by email)
if [ -f "$MERGED" ] && [ -f "$OUTPUT" ]; then
    python3 << PYEOF
import pandas as pd
try:
    existing = pd.read_excel("$OUTPUT")
    new = pd.read_excel("$MERGED")
    for df in (existing, new):
        for c in ["Organisation Name","Category","Location","Email","Phone","Website","Sent"]:
            if c not in df.columns:
                df[c] = ""
    combined = pd.concat([existing, new]).drop_duplicates(subset=["Email"], keep="first")
    combined = combined[combined["Email"].astype(str).str.contains("@", na=False)]
    combined.to_excel("$OUTPUT", index=False)
    print(f"Combined: {len(existing)} curated + {len(new)} scraped = {len(combined)} unique")
except Exception as e:
    print(f"Combine skipped: {e}")
PYEOF
fi

if [ -f "$OUTPUT" ]; then
    echo ""
    echo "========================================="
    echo "STEP 4: Sending outreach emails"
    echo "========================================="
    python3 send_emails.py "$OUTPUT"
else
    echo "No contacts available for $LOCATION / $CATEGORY"
fi
