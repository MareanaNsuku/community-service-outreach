#!/bin/bash
LOCATION="$1"
CATEGORY="$2"

if [ -z "$LOCATION" ] || [ -z "$CATEGORY" ]; then
    echo "Usage: bash send_subset.sh <location> <category>"
    exit 1
fi

SAFE_LOCATION="${LOCATION// /_}"
SAFE_CATEGORY="${CATEGORY// /_}"
OUTPUT="results/auto_${SAFE_LOCATION}_${SAFE_CATEGORY}.xlsx"
mkdir -p results

echo "📌 Sending to $CATEGORY in $LOCATION"
python3 query_master.py "$LOCATION" "$CATEGORY" --output "$OUTPUT"
if [ -f "$OUTPUT" ]; then
    python3 send_emails.py "$OUTPUT"
else
    echo "❌ No contacts found for $LOCATION / $CATEGORY"
fi
