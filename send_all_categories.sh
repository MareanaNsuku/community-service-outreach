#!/bin/bash
LOCATION="$1"
RUN_SLOT="${2:-morning}"

if [ -z "$LOCATION" ]; then
    echo "Usage: bash send_all_categories.sh <location> [morning|evening]"
    exit 1
fi

if [ "$RUN_SLOT" = "morning" ]; then
    CATEGORIES=(
        "Sports & Recreation"
        "Animal Welfare"
        "Environmental"
        "Arts & Culture"
        "Youth & Tutoring"
    )
else
    CATEGORIES=(
        "Health & Wellness"
        "Senior Care"
        "Community Development"
        "Women & Family Support"
        "Emergency & Rescue"
    )
fi

mkdir -p results
echo "=== RUNNING $RUN_SLOT SLOT: ${#CATEGORIES[@]} categories for $LOCATION ==="

for CATEGORY in "${CATEGORIES[@]}"; do
    echo ""
    echo "### CATEGORY: $CATEGORY ###"
    bash send_subset.sh "$LOCATION" "$CATEGORY"
    echo "--- Waiting 30s ---"
    sleep 30
done

echo "=== $RUN_SLOT SLOT COMPLETE ==="
