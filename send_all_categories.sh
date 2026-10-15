#!/bin/bash
# Runs scraper + sender for Mowbray and Rondebosch across many categories.
# Usage: bash send_all_categories.sh [morning|evening]

SLOT="${1:-morning}"

# Strictly target these two suburbs
LOCATIONS=("Mowbray" "Rondebosch")

# Categories split across slots so each cron run finishes in reasonable time.
# Healthcare excluded.

if [ "$SLOT" = "morning" ]; then
    CATEGORIES=(
        # Community + Education
        "Community Development"
        "Youth & Tutoring"
        "Youth Development"
        "Mentorship Programmes"
        "Adult Literacy"
        "Skills Development"
        "Job Training"
        "Early Childhood Development"
        "School Support"
        "Bursary Programmes"
        # Welfare (non-medical)
        "Homeless Shelters"
        "Food Security"
        "Child Welfare"
        "Women's Shelters"
        "Refugee Support"
        "Prison Reform"
        # Civic / Neighbourhood
        "Neighbourhood Watch"
        "Community Policing"
        "Ratepayers Associations"
        "Community Centres"
        "Cultural Centres & Community Halls"
    )
else
    CATEGORIES=(
        # Arts & Culture
        "Arts & Culture"
        "Museums & Heritage"
        "Performing Arts & Music Groups"
        "Community Radio"
        "Community Newspapers"
        # Environment + Animals
        "Environmental"
        "Animal Welfare"
        "Recycling & Waste"
        "Urban Farming"
        "Public Parks & Gardens"
        # Sports + Recreation
        "Sports & Recreation"
        "Sports Clubs"
        "Recreation Centres"
        "Hobby & Special Interest Clubs"
        # Faith
        "Interfaith Organisations"
        "Religious Charities"
        # Misc
        "Emergency & Rescue"
        "Libraries & Reading Programmes"
        "Volunteer Centres & NGO Support"
        "Tourism & Visitor Information"
        "Community Markets & Farmers Markets"
        "Community Events & Festivals"
    )
fi

TOTAL=$(( ${#LOCATIONS[@]} * ${#CATEGORIES[@]} ))

echo "========================================="
echo "Slot:      $SLOT"
echo "Locations: ${LOCATIONS[*]}"
echo "Categories: ${#CATEGORIES[@]}"
echo "Total runs: $TOTAL"
echo "========================================="

for loc in "${LOCATIONS[@]}"; do
    for cat in "${CATEGORIES[@]}"; do
        echo ""
        echo "#########################################"
        echo "# $loc — $cat"
        echo "#########################################"
        bash send_subset.sh "$loc" "$cat" || echo "⚠️  '$loc / $cat' failed, continuing..."
    done
done

echo ""
echo "🎉 Slot '$SLOT' complete — ${TOTAL} runs."
