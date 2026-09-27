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
MASTER_OUTPUT="results/auto_${SAFE_LOCATION}_${SAFE_CATEGORY_CLEAN}_from_master.xlsx"

echo "========================================="
echo "STEP 1: Scraping $CATEGORY in $LOCATION"
echo "========================================="
python3 scraper.py "$LOCATION" "$CATEGORY" || true

# Try merge from scraped
USED_SCRAPED=0
if [ -f "$SCRAPED" ]; then
    echo ""
    echo "========================================="
    echo "STEP 2a: Merging scraped results"
    echo "========================================="
    python3 merge_scraped.py "$SCRAPED" "$OUTPUT" && USED_SCRAPED=1 || true
fi

# Fallback to master file if scraper found nothing
if [ "$USED_SCRAPED" = "0" ] || [ ! -f "$OUTPUT" ]; then
    echo ""
    echo "========================================="
    echo "STEP 2b: Falling back to master_contacts.xlsx"
    echo "========================================="
    python3 query_master.py "$LOCATION" "$CATEGORY" --output "$MASTER_OUTPUT" || true
    if [ -f "$MASTER_OUTPUT" ]; then
        OUTPUT="$MASTER_OUTPUT"
        echo "Using master file: $OUTPUT"
    fi
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
