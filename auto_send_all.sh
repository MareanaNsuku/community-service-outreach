#!/bin/bash
PYTHON="$HOME/Desktop/CommunityServiceOutreach/venv/bin/python"
RESULTS="results"
mkdir -p "$RESULTS"

LOCATIONS=("Randburg" "Sandton" "Johannesburg" "Centurion" "Roodepoort" "Midrand" "Rosebank" "Alberton" "Edenvale" "Soweto" "Boksburg" "Kempton Park" "Krugersdorp" "Daveyton" "Springs")
CATEGORIES=("Sports & Recreation" "Animal Welfare" "Environmental" "Arts & Culture" "Youth & Tutoring")

echo "========================================="
echo "   AUTOMATED OUTREACH – $(date)"
echo "========================================="
echo ""

for loc in "${LOCATIONS[@]}"; do
  safe_loc="${loc// /_}"
  for cat in "${CATEGORIES[@]}"; do
    safe_cat="${cat// /_}"
    out_file="$RESULTS/auto_${safe_loc}_${safe_cat}.xlsx"
    
    echo "📌 $loc – $cat"
    
    # Generate file (returns exit code 0 if contacts found)
    $PYTHON query_master.py "$loc" "$cat" --output "$out_file"
    if [ $? -eq 0 ] && [ -f "$out_file" ]; then
      count=$($PYTHON -c "import pandas as pd; print(len(pd.read_excel('$out_file')))")
      if [ "$count" -gt 0 ]; then
        echo "   📧 Sending $count emails..."
        $PYTHON send_emails.py "$out_file"
      else
        echo "   ⚠️ File empty – skipping."
      fi
    else
      echo "   ❌ No contacts – skipping."
    fi
    echo ""
  done
done

echo "🎉 All locations processed."
