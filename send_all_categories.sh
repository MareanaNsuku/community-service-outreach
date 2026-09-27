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
echo "============================================="
echo "RUNNING ALL CATEGORIES FOR: $LOCATION"
echo "============================================="

for CATEGORY in "${CATEGORIES[@]}"; do
    echo ""
    echo "#############################################"
    echo "# CATEGORY: $CATEGORY"
    echo "#############################################"
    bash send_subset.sh "$LOCATION" "$CATEGORY"
    echo ""
    echo "--- Waiting 30s before next category ---"
    sleep 30
done

echo ""
echo "============================================="
echo "ALL CATEGORIES COMPLETE FOR: $LOCATION"
echo "============================================="
