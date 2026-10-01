#!/bin/bash
LOCATION="$1"

if [ -z "$LOCATION" ]; then
    echo "Usage: bash send_all_categories.sh <location>"
    exit 1
fi

CATEGORIES=(
    "Sports & Recreation"
    "Animal Welfare"
    "Environmental"
    "Arts & Culture"
    "Youth & Tutoring"
    "Health & Wellness"
    "Senior Care"
    "Community Development"
    "Women & Family Support"
    "Emergency & Rescue"
)

mkdir -p results
echo "=== RUNNING ALL CATEGORIES FOR: $LOCATION ==="

for CATEGORY in "${CATEGORIES[@]}"; do
    echo ""
    echo "### CATEGORY: $CATEGORY ###"
    bash send_subset.sh "$LOCATION" "$CATEGORY"
    echo "--- Waiting 30s ---"
    sleep 30
done

echo "=== ALL CATEGORIES COMPLETE ==="
