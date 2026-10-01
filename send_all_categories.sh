#!/bin/bash
SLOT="${1:-morning}"

if [ "$SLOT" = "morning" ]; then
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

echo "========================================="
echo "Running slot: $SLOT (${#CATEGORIES[@]} categories)"
echo "========================================="

for cat in "${CATEGORIES[@]}"; do
    echo ""
    echo "#########################################"
    echo "# CATEGORY: $cat"
    echo "#########################################"
    bash send_subset.sh "Cape Town" "$cat" || echo "⚠️ Category '$cat' failed, continuing..."
done

echo ""
echo "🎉 All categories in $SLOT slot processed."
