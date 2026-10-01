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
        "Museums & Heritage"
        "Libraries & Reading Programmes"
        "Public Parks & Gardens"
        "Cultural Centres & Community Halls"
    )
else
    CATEGORIES=(
        "Historic Sites & Preservation"
        "Neighbourhood Associations"
        "Community Media & Radio"
        "Community Markets & Farmers Markets"
        "Performing Arts & Music Groups"
        "Adult Education & Skills Training"
        "Volunteer Centres & NGO Support"
        "Tourism & Visitor Information"
        "Community Events & Festivals"
        "Hobby & Special Interest Clubs"
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
