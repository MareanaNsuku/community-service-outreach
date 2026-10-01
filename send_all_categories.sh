#!/bin/bash
RUN_SLOT="${1:-morning}"
LOCATION="Cape Town"

if [ "$RUN_SLOT" = "morning" ]; then
    CATEGORIES=(
        "Sports & Recreation"
        "Animal Welfare"
        "Environmental"
        "Arts & Culture"
        "Youth & Tutoring"
        "Community Development"
    )
else
    CATEGORIES=(
        "Emergency & Rescue"
        "Substance Abuse Recovery"
        "Refugee & Migrant Support"
        "Community Safety"
        "Prison & Rehabilitation"
        "Legal Aid & Human Rights"
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
