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
OUTPUT="results/auto_${SAFE_LOCATION}_${SAFE_CATEGORY_CLEAN}.xlsx"

echo "========================================="
echo "STEP 1: Scraping $CATEGORY in $LOCATION"
echo "========================================="
python3 scraper.py "$LOCATION" "$CATEGORY"

if [ ! -f "$SCRAPED" ]; then
    echo "Scraper found no results. Falling back to master file."
    python3 query_master.py "$LOCATION" "$CATEGORY" --output "$OUTPUT"
else
    echo ""
    echo "========================================="
    echo "STEP 2: Merging scraped results into send queue"
    echo "========================================="
    python3 merge_scraped.py "$SCRAPED" "$OUTPUT"
fi

if [ -f "$OUTPUT" ]; then
    echo ""
    echo "========================================="
    echo "STEP 3: Sending outreach emails"
    echo "========================================="
    python3 send_emails.py "$OUTPUT"
else
    echo "No contacts available for $LOCATION / $CATEGORY"
fi
